"""Haltbarkeits- und Bestandsstatus (FR-EXP-002/003/006, FR-SHP-003/004).

Reine Funktionen ohne Datenbankzugriff, damit die Regeln isoliert testbar sind.
"""

import enum
from datetime import date
from decimal import ROUND_CEILING, Decimal


class ExpiryStatus(enum.StrEnum):
    OK = "ok"  # Grün: kein aktueller Handlungsbedarf
    EXPIRING = "expiring"  # Gelb: Datum liegt innerhalb der Warnfrist
    DUE = "due"  # Rot: Datum heute erreicht
    EXPIRED = "expired"  # Rot: Datum überschritten
    UNKNOWN = "unknown"  # Grau: kein Datum vorhanden oder unbekannt


class StockLevelStatus(enum.StrEnum):
    OK = "ok"  # Ausreichend
    NEAR = "near"  # Nahe am Mindestbestand (≤ Mindestbestand × Warnfaktor)
    AT_MINIMUM = "at_minimum"  # Mindestbestand erreicht
    BELOW = "below"  # Mindestbestand unterschritten


def expiry_status(expiry_date: date | None, warning_days: int, today: date) -> ExpiryStatus:
    """Ampelstatus einer Bestandsposition. Ohne Datum (Typ „kein“/„unbekannt“) → grau."""
    if expiry_date is None:
        return ExpiryStatus.UNKNOWN
    if expiry_date < today:
        return ExpiryStatus.EXPIRED
    if expiry_date == today:
        return ExpiryStatus.DUE
    if (expiry_date - today).days <= warning_days:
        return ExpiryStatus.EXPIRING
    return ExpiryStatus.OK


def stock_level_status(
    available: Decimal, minimum: Decimal, warning_factor: Decimal
) -> StockLevelStatus:
    """Bestandsstatus gegenüber dem Mindestbestand (FR-SHP-003/004).

    Beispiel Mindestbestand 4, Faktor 1,25: 7 → ok, 5 → nahe, 4 → erreicht, 3 → unterschritten.
    """
    if available < minimum:
        return StockLevelStatus.BELOW
    if available == minimum:
        return StockLevelStatus.AT_MINIMUM
    if available <= minimum * warning_factor:
        return StockLevelStatus.NEAR
    return StockLevelStatus.OK


def restock_quantity(
    available: Decimal,
    minimum: Decimal,
    target: Decimal | None,
    package_size: Decimal | None = None,
) -> Decimal | None:
    """Vorgeschlagene Einkaufsmenge (FR-SHP-006): Zielbestand − verfügbarer Bestand, ohne
    Zielbestand bis zum Mindestbestand. Mit bekannter Packungsgröße wird auf ganze Packungen
    aufgerundet. Ergibt die Differenz nichts (z. B. genau am Mindestbestand ohne Zielbestand),
    wird eine Packung vorgeschlagen; ohne Packungsgröße bleibt die Menge offen (None).

    Beispiel: Ziel 6 l, Bestand 1 l → 5 l; bei 1-l-Packungen 5 Packungen."""
    goal = target if target is not None else minimum
    missing = goal - available
    if missing <= 0:
        return package_size
    if package_size:
        packages = (missing / package_size).to_integral_value(rounding=ROUND_CEILING)
        return packages * package_size
    return missing

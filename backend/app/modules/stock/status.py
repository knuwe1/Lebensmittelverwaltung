"""Haltbarkeits- und Bestandsstatus (FR-EXP-002/003/006, FR-SHP-003/004).

Reine Funktionen ohne Datenbankzugriff, damit die Regeln isoliert testbar sind.
"""

import enum
from datetime import date
from decimal import Decimal


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

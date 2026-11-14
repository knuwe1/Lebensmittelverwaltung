"""Restmenge per Waage erfassen (DEC-029).

Der Benutzer wiegt nach einer Entnahme die angebrochene Packung. Aus der Differenz
zwischen erwarteter und gewogener Menge ergibt sich der Verbrauch.

Annahmen (vom Product Owner festgelegt):
- Ein hinterlegtes Leergewicht der Verpackungsvariante wird vom abgelesenen Gewicht abgezogen.
- Enthält eine Position mehrere Packungen, ist höchstens eine angebrochen; alle anderen
  gelten als voll. Gewogen wird nur die angebrochene Packung.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from app.core.errors import ValidationFailed
from app.core.units import normalize


@dataclass(frozen=True)
class WeighResult:
    measured: Decimal  # abgelesenes Gewicht
    tare: Decimal  # abgezogenes Leergewicht
    net: Decimal  # tatsächlicher Inhalt der angebrochenen Packung
    full_packages: int  # Anzahl als voll angenommener Packungen
    open_before: Decimal  # erwarteter Inhalt der angebrochenen Packung vor dem Wiegen
    consumption: Decimal  # zu buchender Verbrauch
    remaining_total: Decimal  # Bestand der Position nach der Buchung


def compute_weighing(
    position_quantity: Decimal,
    measured: Decimal,
    package_size: Decimal | None = None,
    tare: Decimal | None = None,
) -> WeighResult:
    tare = tare or Decimal(0)
    net = normalize(measured - tare)
    if net < 0:
        raise ValidationFailed(
            "Das gewogene Gewicht ist kleiner als das Leergewicht der Verpackung.",
            code="below_tare",
        )

    full = 0
    if package_size and position_quantity > package_size:
        packages = (position_quantity / package_size).to_integral_value(rounding=ROUND_CEILING)
        full = int(packages) - 1
    open_before = normalize(position_quantity - full * (package_size or 0))

    consumption = normalize(open_before - net)
    if consumption < 0:
        raise ValidationFailed(
            "Die gewogene Menge ist größer als der erwartete Inhalt der angebrochenen Packung "
            f"({open_before} g). Bitte Gewicht und Leergewicht prüfen oder den Bestand per "
            "Inventur korrigieren.",
            code="weight_above_expected",
            details={"open_before": float(open_before), "net": float(net)},
        )
    return WeighResult(
        measured=normalize(measured),
        tare=normalize(tare),
        net=net,
        full_packages=full,
        open_before=open_before,
        consumption=consumption,
        remaining_total=normalize(position_quantity - consumption),
    )

"""Mengeneinheiten und Umrechnung (Spezifikation 4.3, DEC-011, DEC-023).

Bestände werden ausschließlich in der Basiseinheit des Produkts geführt:
Stück, Gramm oder Milliliter. Verpackungsangaben dürfen in kg bzw. l erfolgen und
werden umgerechnet. Zwischen Masse, Volumen und Stück wird nie automatisch umgerechnet.
"""

import enum
from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

from app.core.errors import ValidationFailed

QUANTITY_PLACES = 3
_STEP = Decimal("0.001")


class BaseUnit(enum.StrEnum):
    PIECE = "piece"
    GRAM = "g"
    MILLILITER = "ml"


class PackageUnit(enum.StrEnum):
    PIECE = "piece"
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"


# Faktor und zugehörige Basiseinheit je Verpackungseinheit
_PACKAGE_FACTORS: dict[PackageUnit, tuple[BaseUnit, Decimal]] = {
    PackageUnit.PIECE: (BaseUnit.PIECE, Decimal(1)),
    PackageUnit.GRAM: (BaseUnit.GRAM, Decimal(1)),
    PackageUnit.KILOGRAM: (BaseUnit.GRAM, Decimal(1000)),
    PackageUnit.MILLILITER: (BaseUnit.MILLILITER, Decimal(1)),
    PackageUnit.LITER: (BaseUnit.MILLILITER, Decimal(1000)),
}


def compatible_package_units(base: BaseUnit) -> list[PackageUnit]:
    return [p for p, (b, _) in _PACKAGE_FACTORS.items() if b == base]


def to_base_quantity(amount: Decimal, unit: PackageUnit, base: BaseUnit) -> Decimal:
    """Rechnet eine Verpackungsangabe in die Basiseinheit um, z. B. 1,5 kg → 1500 g."""
    target, factor = _PACKAGE_FACTORS[unit]
    if target != base:
        raise ValidationFailed(
            f"Die Einheit '{unit.value}' passt nicht zur Basiseinheit '{base.value}' des "
            "Produkts. Masse, Volumen und Stück werden nicht ineinander umgerechnet.",
            code="incompatible_unit",
        )
    return normalize(amount * factor)


def normalize(value: Decimal) -> Decimal:
    """Rundet auf die gespeicherte Genauigkeit (drei Nachkommastellen)."""
    return value.quantize(_STEP)


def _as_number(value: Decimal) -> float:
    return float(value)


# Mengen werden als Decimal verarbeitet und in JSON als Zahl ausgegeben.
Quantity = Annotated[
    Decimal,
    Field(max_digits=14, decimal_places=QUANTITY_PLACES),
    PlainSerializer(_as_number, return_type=float, when_used="json"),
]
PositiveQuantity = Annotated[Quantity, Field(gt=0)]
NonNegativeQuantity = Annotated[Quantity, Field(ge=0)]

from decimal import Decimal

import pytest

from app.core.barcodes import normalize_barcode
from app.core.errors import ValidationFailed
from app.core.units import BaseUnit, PackageUnit, compatible_package_units, to_base_quantity


@pytest.mark.parametrize(
    ("amount", "unit", "base", "expected"),
    [
        ("500", PackageUnit.GRAM, BaseUnit.GRAM, "500"),
        ("1", PackageUnit.KILOGRAM, BaseUnit.GRAM, "1000"),
        ("2.5", PackageUnit.KILOGRAM, BaseUnit.GRAM, "2500"),
        ("1", PackageUnit.LITER, BaseUnit.MILLILITER, "1000"),
        ("0.33", PackageUnit.LITER, BaseUnit.MILLILITER, "330"),
        ("6", PackageUnit.PIECE, BaseUnit.PIECE, "6"),
        ("0.5", PackageUnit.PIECE, BaseUnit.PIECE, "0.5"),  # DEC-023
    ],
)
def test_conversion_to_base_unit(amount, unit, base, expected):
    assert to_base_quantity(Decimal(amount), unit, base) == Decimal(expected)


@pytest.mark.parametrize(
    ("unit", "base"),
    [
        (PackageUnit.LITER, BaseUnit.GRAM),
        (PackageUnit.KILOGRAM, BaseUnit.MILLILITER),
        (PackageUnit.GRAM, BaseUnit.PIECE),
        (PackageUnit.PIECE, BaseUnit.GRAM),
    ],
)
def test_no_conversion_between_mass_volume_and_pieces(unit, base):
    with pytest.raises(ValidationFailed):
        to_base_quantity(Decimal(1), unit, base)


def test_compatible_units():
    assert set(compatible_package_units(BaseUnit.GRAM)) == {PackageUnit.GRAM, PackageUnit.KILOGRAM}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4006381333931", "4006381333931"),  # EAN-13
        ("96385074", "96385074"),  # EAN-8
        ("036000291452", "0036000291452"),  # UPC-A → EAN-13
        ("4006 3813-33931", "4006381333931"),
        ("2100123", "2100123"),  # Hauscode ohne Prüfziffernkontrolle
    ],
)
def test_barcode_normalization(raw, expected):
    assert normalize_barcode(raw) == expected


@pytest.mark.parametrize("raw", ["4006381333932", "abc", "12345", "123456789012345"])
def test_invalid_barcodes(raw):
    with pytest.raises(ValidationFailed):
        normalize_barcode(raw)

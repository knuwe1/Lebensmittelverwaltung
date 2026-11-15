"""Barcode-Normalisierung und -Prüfung (FR-PRD-002).

Unterstützt werden mindestens EAN-13, EAN-8 und UPC-A. UPC-A (12 Stellen) wird als
EAN-13 mit führender Null gespeichert, damit dasselbe Produkt unabhängig vom
Scanner-Ergebnis gefunden wird. Andere numerische Codes (6–14 Stellen, z. B.
Hauscodes von Händlern) werden ohne Prüfziffernkontrolle akzeptiert.
"""

import re

from app.core.errors import ValidationFailed

_DIGITS = re.compile(r"^\d{6,14}$")


def gtin_check_digit_valid(code: str) -> bool:
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def normalize_barcode(raw: str) -> str:
    code = re.sub(r"[\s-]", "", raw or "")
    if not _DIGITS.match(code):
        raise ValidationFailed(
            "Der Barcode muss aus 6 bis 14 Ziffern bestehen.", code="invalid_barcode"
        )
    if len(code) in (8, 12, 13, 14) and not gtin_check_digit_valid(code):
        raise ValidationFailed(
            "Die Prüfziffer des Barcodes ist ungültig. Bitte erneut scannen.",
            code="invalid_barcode_checksum",
        )
    if len(code) == 12:  # UPC-A → EAN-13
        code = "0" + code
    return code

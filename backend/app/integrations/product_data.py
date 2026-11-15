"""Externe Produktdaten anhand eines Barcodes (FR-PRD-003, DEC-028).

Austauschbare Schnittstelle ``ProductDataSource``; erste Implementierung: Open Food Facts.
Übermittelt wird ausschließlich der Barcode – keine Bestands- oder Haushaltsdaten.
Ergebnisse sind nur Vorschläge, die der Benutzer vor dem Speichern prüft (R-004).
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

USER_AGENT = "Lebensmittelverwaltung/0.1 (self-hosted household inventory)"


class ExternalServiceError(Exception):
    """Dienst nicht erreichbar oder fehlerhafte Antwort."""


@dataclass
class ProductSuggestion:
    source: str
    source_url: str
    license: str
    barcode: str
    name: str | None
    brand: str | None
    base_unit: str
    package_quantity: Decimal | None
    package_unit: str | None
    category_hint: str | None  # Name einer Standard-Produktgruppe
    image_url: str | None


class ProductDataSource(Protocol):
    name: str

    def lookup(self, barcode: str) -> ProductSuggestion | None: ...

    def fetch_image(self, url: str) -> bytes: ...


# Open-Food-Facts-Kategorien → Standard-Produktgruppen (Spez. 4.2). Reihenfolge = Priorität.
_CATEGORY_MAP: list[tuple[tuple[str, ...], str]] = [
    (("en:frozen-foods",), "Tiefkühlprodukte"),
    (("en:canned-foods",), "Konserven"),
    (("en:dairies", "en:milks", "en:cheeses", "en:yogurts", "en:butters"), "Milchprodukte"),
    (("en:fishes", "en:seafood"), "Fisch"),
    (("en:meats", "en:sausages", "en:hams"), "Fleisch und Wurst"),
    (("en:breads", "en:biscuits-and-cakes", "en:pastries"), "Brot und Backwaren"),
    (
        ("en:pastas", "en:rices", "en:cereals-and-their-products", "en:flours"),
        "Nudeln, Reis und Getreide",
    ),
    (("en:fruits", "en:fresh-fruits"), "Obst"),
    (("en:vegetables", "en:fresh-vegetables"), "Gemüse"),
    (("en:beverages", "en:waters", "en:juices"), "Getränke"),
    (("en:spices", "en:condiments", "en:salts", "en:herbs"), "Gewürze"),
    (
        (
            "en:sweets",
            "en:chocolates",
            "en:confectioneries",
            "en:sugars",
            "en:snacks",
            "en:sweet-spreads",
            "en:chocolate-spreads",
            "en:confectionary-based-spreads",
        ),
        "Süßwaren",
    ),
]

_UNIT_MAP = {
    "g": ("g", "g", Decimal(1)),
    "kg": ("g", "kg", Decimal(1)),
    "mg": ("g", "g", Decimal("0.001")),
    "ml": ("ml", "ml", Decimal(1)),
    "cl": ("ml", "ml", Decimal(10)),
    "dl": ("ml", "ml", Decimal(100)),
    "l": ("ml", "l", Decimal(1)),
}
_QTY = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(kg|g|mg|ml|cl|dl|l)\b", re.IGNORECASE)


def _plain(value: Decimal) -> Decimal:
    """Ohne Exponentenschreibweise: 4E+2 → 400, 1.500 → 1.5."""
    return value.quantize(Decimal(1)) if value == value.to_integral_value() else value.normalize()


def _category_hint(tags: list[str]) -> str | None:
    for keys, name in _CATEGORY_MAP:
        if any(k in tags for k in keys):
            return name
    return None


def _quantity(product: dict) -> tuple[str, Decimal | None, str | None]:
    """Basiseinheit und Packungsgröße aus den OFF-Feldern ableiten."""
    raw_qty, raw_unit = product.get("product_quantity"), product.get("product_quantity_unit")
    if raw_qty and raw_unit and raw_unit.lower() in _UNIT_MAP:
        base, unit, factor = _UNIT_MAP[raw_unit.lower()]
        try:
            qty = Decimal(str(raw_qty)) * factor
        except InvalidOperation:
            qty = None
        if qty and qty > 0:
            return base, _plain(qty), unit if factor == 1 else base
    match = _QTY.match(product.get("quantity") or "")
    if match:
        base, unit, factor = _UNIT_MAP[match.group(2).lower()]
        qty = Decimal(match.group(1).replace(",", ".")) * factor
        return base, _plain(qty), unit if factor == 1 else base
    return "piece", None, None


class OpenFoodFacts:
    name = "Open Food Facts"
    license = "Daten: ODbL · Bilder: CC BY-SA 3.0"
    image_hosts = ("images.openfoodfacts.org", "static.openfoodfacts.org")

    def __init__(self, client: httpx.Client | None = None, base_url: str | None = None):
        self.base_url = (base_url or get_settings().off_base_url).rstrip("/")
        self.client = client or httpx.Client(
            timeout=5.0, headers={"User-Agent": USER_AGENT}, follow_redirects=False
        )

    def lookup(self, barcode: str) -> ProductSuggestion | None:
        fields = (
            "product_name,product_name_de,brands,quantity,product_quantity,"
            "product_quantity_unit,categories_tags,image_front_url"
        )
        try:
            r = self.client.get(
                f"{self.base_url}/api/v2/product/{barcode}", params={"fields": fields}
            )
        except httpx.HTTPError as exc:
            log.warning("Open Food Facts nicht erreichbar: %s", exc)
            raise ExternalServiceError from exc
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            log.warning("Open Food Facts antwortete mit %s", r.status_code)
            raise ExternalServiceError
        data = r.json()
        if data.get("status") != 1 or not data.get("product"):
            return None
        p = data["product"]
        base_unit, pkg_qty, pkg_unit = _quantity(p)
        brand = (p.get("brands") or "").split(",")[0].strip() or None
        image = p.get("image_front_url")
        return ProductSuggestion(
            source=self.name,
            source_url=f"https://world.openfoodfacts.org/product/{barcode}",
            license=self.license,
            barcode=barcode,
            name=(p.get("product_name_de") or p.get("product_name") or "").strip() or None,
            brand=brand,
            base_unit=base_unit,
            package_quantity=pkg_qty,
            package_unit=pkg_unit,
            category_hint=_category_hint(p.get("categories_tags") or []),
            image_url=image if self.is_allowed_image(image) else None,
        )

    def is_allowed_image(self, url: str | None) -> bool:
        return bool(url) and any(url.startswith(f"https://{h}/") for h in self.image_hosts)

    def fetch_image(self, url: str) -> bytes:
        if not self.is_allowed_image(url):
            raise ExternalServiceError("Bildquelle nicht zulässig")
        limit = get_settings().max_upload_bytes
        try:
            with self.client.stream("GET", url) as r:
                if r.status_code != 200:
                    raise ExternalServiceError
                data = b""
                for chunk in r.iter_bytes():
                    data += chunk
                    if len(data) > limit:
                        raise ExternalServiceError("Bild zu groß")
                return data
        except httpx.HTTPError as exc:
            raise ExternalServiceError from exc


def get_product_data_source() -> ProductDataSource:
    """FastAPI-Abhängigkeit; in Tests überschreibbar."""
    return OpenFoodFacts()

import enum
import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.units import BaseUnit, PositiveQuantity, Quantity
from app.modules.catalog.schemas import ProductOut
from app.modules.stock.models import ExpiryType, StockStatus


class LineUnit(enum.StrEnum):
    PACKAGE = "package"  # Anzahl Packungen der gewählten Variante
    BASE = "base"  # Menge direkt in der Basiseinheit des Produkts


class ReceiptLine(BaseModel):
    """Eine Teilmenge mit einheitlichem Haltbarkeitsdatum (FR-STK-003)."""

    quantity: PositiveQuantity
    unit: LineUnit = LineUnit.PACKAGE
    expiry_type: ExpiryType = ExpiryType.UNKNOWN
    expiry_date: date | None = None

    @model_validator(mode="after")
    def _expiry(self):
        needs_date = self.expiry_type in (ExpiryType.BEST_BEFORE, ExpiryType.USE_BY)
        if needs_date and self.expiry_date is None:
            raise ValueError("Für MHD bzw. Verbrauchsdatum muss ein Datum angegeben werden.")
        if not needs_date and self.expiry_date is not None:
            raise ValueError("Ein Datum ist nur bei MHD oder Verbrauchsdatum zulässig.")
        return self


class ReceiptCreate(BaseModel):
    """Einlagerung (FR-STK-001/002/003). Mehrere Zeilen = unterschiedliche Haltbarkeitsdaten."""

    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    location_id: uuid.UUID
    lines: list[ReceiptLine] = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=2000)


class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_brand: str | None
    base_unit: BaseUnit
    variant_id: uuid.UUID | None
    location_id: uuid.UUID
    location_path: str
    quantity: Quantity
    expiry_type: ExpiryType
    expiry_date: date | None
    received_on: date
    opened_on: date | None
    status: StockStatus
    note: str | None
    version: int


class StockPage(BaseModel):
    items: list[StockItemOut]
    total: int


class ReceiptResult(BaseModel):
    transaction_id: uuid.UUID
    product: ProductOut
    stock_items: list[StockItemOut]
    received_quantity: Quantity


class ReceiptDefaults(BaseModel):
    """Vorschlagswerte für die Einlagerung bekannter Produkte (FR-STK-001)."""

    variant_id: uuid.UUID | None
    location_id: uuid.UUID | None
    expiry_type: ExpiryType
    expiry_date: date | None

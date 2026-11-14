import enum
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.units import BaseUnit, NonNegativeQuantity, PositiveQuantity, Quantity
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


# ------------------------------------------------------------------ Phase 3: Bewegungen


class DisposalReason(enum.StrEnum):
    EXPIRED = "expired"  # Haltbarkeit überschritten
    SPOILED = "spoiled"  # Verdorben
    DAMAGED = "damaged"  # Beschädigt
    OTHER = "other"  # Sonstiger Grund


class AllocationIn(BaseModel):
    """Konkrete Entnahme aus einer Bestandsposition (FR-CNS-002: nachvollziehbar, welcher
    Bestand reduziert wird). ``expected_version`` erkennt zwischenzeitliche Änderungen."""

    stock_item_id: uuid.UUID
    quantity: PositiveQuantity
    expected_version: int | None = None


class ConsumptionCreate(BaseModel):
    """Verbrauch buchen. Entweder explizite ``allocations`` (z. B. bestätigter Vorschlag)
    oder ``quantity`` – dann verteilt der Server nach FEFO."""

    product_id: uuid.UUID
    allocations: list[AllocationIn] | None = Field(default=None, max_length=100)
    quantity: PositiveQuantity | None = None
    unit: LineUnit = LineUnit.BASE
    variant_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _one_of(self):
        if bool(self.allocations) == (self.quantity is not None):
            raise ValueError("Entweder 'allocations' oder 'quantity' angeben.")
        return self


class DisposalCreate(BaseModel):
    product_id: uuid.UUID
    allocations: list[AllocationIn] = Field(min_length=1, max_length=100)
    reason: DisposalReason
    comment: str | None = Field(default=None, max_length=2000)


class TransferCreate(BaseModel):
    stock_item_id: uuid.UUID
    quantity: PositiveQuantity
    target_location_id: uuid.UUID
    expected_version: int | None = None
    comment: str | None = Field(default=None, max_length=2000)


class ReversalCreate(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class PlannedAllocation(BaseModel):
    stock_item: StockItemOut
    quantity: Quantity


class ConsumptionPlan(BaseModel):
    allocations: list[PlannedAllocation]
    requested: Quantity
    available: Quantity
    sufficient: bool


class BookingResult(BaseModel):
    transaction_id: uuid.UUID
    product: ProductOut
    # Betroffene Positionen nach der Buchung (Menge 0 = aufgelöst)
    stock_items: list[StockItemOut]
    quantity: Quantity


class MovementOut(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    movement_type: str
    product_id: uuid.UUID
    product_name: str
    base_unit: BaseUnit
    stock_item_id: uuid.UUID
    expiry_type: ExpiryType
    expiry_date: date | None
    source_location_path: str | None
    target_location_path: str | None
    quantity: Quantity
    quantity_delta: Quantity
    reason: str | None
    comment: str | None
    created_at: datetime
    created_by: uuid.UUID
    created_by_name: str
    reverses_movement_id: uuid.UUID | None
    reversed: bool


class MovementPage(BaseModel):
    items: list[MovementOut]
    total: int


class WeighingCreate(BaseModel):
    """Restmenge per Waage: abgelesenes Gewicht der angebrochenen Packung (DEC-029)."""

    stock_item_id: uuid.UUID
    measured_weight: NonNegativeQuantity
    expected_version: int | None = None
    comment: str | None = Field(default=None, max_length=2000)


class WeighingPreview(BaseModel):
    measured: Quantity
    tare: Quantity
    net: Quantity
    full_packages: int
    open_before: Quantity
    consumption: Quantity
    remaining_total: Quantity

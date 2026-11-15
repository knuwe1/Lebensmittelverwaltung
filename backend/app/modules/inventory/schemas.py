import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.units import BaseUnit, NonNegativeQuantity, PositiveQuantity, Quantity
from app.modules.inventory.models import InventoryStatus
from app.modules.stock.models import ExpiryType


class InventoryCreate(BaseModel):
    """FR-INV-001: einzelner Lagerplatz, mit Unterlagerplätzen oder gesamter Haushalt (ohne
    `location_id`)."""

    location_id: uuid.UUID | None = None
    include_sublocations: bool = True
    note: str | None = Field(default=None, max_length=2000)


class InventoryItemOut(BaseModel):
    id: uuid.UUID
    stock_item_id: uuid.UUID | None
    is_new: bool
    product_id: uuid.UUID
    product_name: str
    product_brand: str | None
    base_unit: BaseUnit
    variant_id: uuid.UUID | None
    location_id: uuid.UUID
    location_path: str
    expiry_type: ExpiryType
    expiry_date: date | None
    # Soll = dokumentierter Bestand beim Start bzw. bei der letzten Prüfung (FR-INV-002)
    expected_quantity: Quantity
    counted_quantity: Quantity | None
    # Ist − Soll, sobald gezählt (FR-INV-003)
    difference: Quantity | None
    # Aktueller Buchbestand der Position; weicht er vom Soll ab, wurde zwischenzeitlich
    # gebucht und die Position muss erneut geprüft werden (FR-INV-008)
    current_quantity: Quantity | None
    conflict: bool
    # changed = seit dem Start gebucht, new = seit dem Start neu entstandene Position
    conflict_reason: Literal["changed", "new"] | None
    note: str | None
    counted_at: datetime | None
    applied_delta: Quantity | None


class InventorySummary(BaseModel):
    total: int
    counted: int
    differences: int
    conflicts: int


class InventoryOut(BaseModel):
    id: uuid.UUID
    status: InventoryStatus
    location_id: uuid.UUID | None
    # „Gesamter Haushalt“ oder Pfad des Lagerplatzes (mit Hinweis auf Unterlagerplätze)
    scope_label: str
    include_sublocations: bool
    location_ids: list[uuid.UUID]
    location_paths: list[str]
    note: str | None
    started_at: datetime
    started_by_name: str
    completed_at: datetime | None
    completed_by_name: str | None
    transaction_id: uuid.UUID | None
    summary: InventorySummary
    items: list[InventoryItemOut] | None = None


class CountUpdate(BaseModel):
    """Gezählter Istbestand einer Position. Das Zählen einer Position mit Konflikt gilt als
    erneute Prüfung: der aktuelle Buchbestand wird zum neuen Soll (FR-INV-008)."""

    counted_quantity: NonNegativeQuantity | None
    note: str | None = Field(default=None, max_length=2000)


class InventoryItemCreate(BaseModel):
    """Bisher nicht erfasstes Lebensmittel ergänzen (FR-INV-005)."""

    product_id: uuid.UUID
    location_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    expiry_type: ExpiryType = ExpiryType.UNKNOWN
    expiry_date: date | None = None
    counted_quantity: PositiveQuantity
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _expiry(self):
        needs_date = self.expiry_type in (ExpiryType.BEST_BEFORE, ExpiryType.USE_BY)
        if needs_date != (self.expiry_date is not None):
            raise ValueError("Ein Datum ist genau bei MHD oder Verbrauchsdatum anzugeben.")
        return self


class InventoryConflict(BaseModel):
    item_id: uuid.UUID
    product_name: str
    location_path: str
    reason: str

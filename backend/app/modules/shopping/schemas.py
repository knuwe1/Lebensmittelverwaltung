import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core.units import BaseUnit, PositiveQuantity, Quantity
from app.modules.shopping.models import ItemOrigin, ItemStatus
from app.modules.stock.status import StockLevelStatus


class PackageInfo(BaseModel):
    """Standardverpackung des Produkts, auf die Vorschläge aufgerundet werden (FR-SHP-006)."""

    variant_id: uuid.UUID
    package_quantity: Quantity
    package_unit: str
    base_quantity: Quantity
    name: str | None


class ShoppingItemOut(BaseModel):
    id: uuid.UUID
    origin: ItemOrigin
    optional: bool
    status: ItemStatus
    product_id: uuid.UUID | None
    # Produktname bzw. freier Text
    name: str
    brand: str | None
    category_name: str | None
    base_unit: BaseUnit | None
    suggested_quantity: Quantity | None
    # Wirksame Menge: manuell angepasst, sonst der Vorschlag
    quantity: Quantity | None
    quantity_adjusted: bool
    package: PackageInfo | None
    # Anzahl Packungen, wenn die Menge ganze Standardpackungen ergibt
    packages: Quantity | None
    received_quantity: Quantity
    comment: str | None
    # Bestandsinformationen (FR-SHP-005)
    available_quantity: Quantity | None
    minimum_stock: Quantity | None
    target_stock: Quantity | None
    level_status: StockLevelStatus | None
    purchased_at: datetime | None
    created_at: datetime


class ShoppingListOut(BaseModel):
    id: uuid.UUID
    name: str
    items: list[ShoppingItemOut]


class RefreshResult(BaseModel):
    added: int
    updated: int
    removed: int
    list: ShoppingListOut


class ShoppingItemCreate(BaseModel):
    """Manuelle Position (FR-SHP-007): ein Produkt aus dem Katalog oder ein freier Text."""

    product_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: PositiveQuantity | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _product_or_name(self):
        if (self.product_id is None) == (self.name is None or not self.name.strip()):
            raise ValueError("Entweder ein Lebensmittel oder einen Text angeben.")
        if self.name:
            self.name = self.name.strip()
        return self


class EditableStatus(enum.StrEnum):
    OPEN = "open"
    PURCHASED = "purchased"
    DONE = "done"  # erledigt, ohne einzulagern (ändert den Bestand nicht)


class ShoppingItemUpdate(BaseModel):
    """Änderungen an einer Position. `quantity: null` setzt auf den Vorschlag zurück."""

    quantity: PositiveQuantity | None = None
    comment: str | None = Field(default=None, max_length=2000)
    # Nur `false` ist sinnvoll: optionale Position übernehmen
    optional: bool | None = None
    status: EditableStatus | None = None

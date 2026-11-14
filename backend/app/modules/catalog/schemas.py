import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.units import BaseUnit, NonNegativeQuantity, PackageUnit, PositiveQuantity, Quantity


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sort_order: int
    active: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = None
    active: bool | None = None


class VariantIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    barcode: str | None = Field(default=None, max_length=32)
    package_quantity: PositiveQuantity
    package_unit: PackageUnit
    tare_weight: NonNegativeQuantity | None = None
    is_default: bool = False


class VariantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    barcode: str | None = Field(default=None, max_length=32)
    package_quantity: PositiveQuantity | None = None
    package_unit: PackageUnit | None = None
    tare_weight: NonNegativeQuantity | None = None
    is_default: bool | None = None


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    barcode: str | None
    package_quantity: Quantity
    package_unit: PackageUnit
    base_quantity: Quantity
    tare_weight: Quantity | None
    is_default: bool
    active: bool


def _check_min_target(minimum, target) -> None:
    if minimum is not None and target is not None and target < minimum:
        raise ValueError("Der Zielbestand darf nicht kleiner als der Mindestbestand sein.")


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: uuid.UUID
    base_unit: BaseUnit
    brand: str | None = Field(default=None, max_length=200)
    minimum_stock: NonNegativeQuantity | None = None
    target_stock: NonNegativeQuantity | None = None
    default_location_id: uuid.UUID | None = None
    default_shelf_life_days: int | None = Field(default=None, ge=0, le=36500)
    expiry_warning_days: int | None = Field(default=None, ge=0, le=3650)
    notes: str | None = Field(default=None, max_length=5000)
    image_source: str | None = Field(default=None, max_length=200)
    weigh_remaining: bool = False
    # Bild aus einer externen Produktdatenquelle übernehmen (nur zulässige Quellen)
    external_image_url: str | None = Field(default=None, max_length=1000)
    variants: list[VariantIn] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _min_target(self):
        _check_min_target(self.minimum_stock, self.target_stock)
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    base_unit: BaseUnit | None = None
    brand: str | None = Field(default=None, max_length=200)
    minimum_stock: NonNegativeQuantity | None = None
    target_stock: NonNegativeQuantity | None = None
    default_location_id: uuid.UUID | None = None
    default_shelf_life_days: int | None = Field(default=None, ge=0, le=36500)
    expiry_warning_days: int | None = Field(default=None, ge=0, le=3650)
    notes: str | None = Field(default=None, max_length=5000)
    weigh_remaining: bool | None = None
    active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    brand: str | None
    category_id: uuid.UUID
    category_name: str
    base_unit: BaseUnit
    minimum_stock: Quantity | None
    target_stock: Quantity | None
    default_location_id: uuid.UUID | None
    default_shelf_life_days: int | None
    expiry_warning_days: int | None
    notes: str | None
    weigh_remaining: bool
    active: bool
    has_image: bool
    image_source: str | None
    variants: list[VariantOut]
    # Physisch vorhandene Menge in der Basiseinheit (Summe aller Bestandspositionen)
    stock_quantity: Quantity
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int


class BarcodeLookup(BaseModel):
    product: ProductOut
    variant_id: uuid.UUID

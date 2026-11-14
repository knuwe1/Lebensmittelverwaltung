import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.units import BaseUnit, PackageUnit
from app.db.base import Base, Timestamps, UUIDPk, str_enum

QTY = Numeric(14, 3)

DEFAULT_CATEGORIES = [
    "Milchprodukte",
    "Fleisch und Wurst",
    "Fisch",
    "Obst",
    "Gemüse",
    "Brot und Backwaren",
    "Nudeln, Reis und Getreide",
    "Konserven",
    "Tiefkühlprodukte",
    "Getränke",
    "Gewürze",
    "Süßwaren",
    "Sonstige Lebensmittel",
]


class ProductCategory(UUIDPk, Timestamps, Base):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("household_id", "name"),)

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Product(UUIDPk, Timestamps, Base):
    """Lebensmittelprodukt (Spezifikation 4.2)."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("minimum_stock IS NULL OR minimum_stock >= 0", name="minimum_stock"),
        CheckConstraint(
            "target_stock IS NULL OR minimum_stock IS NULL OR target_stock >= minimum_stock",
            name="target_ge_minimum",
        ),
        CheckConstraint(
            "expiry_warning_days IS NULL OR expiry_warning_days >= 0", name="warning_days"
        ),
        CheckConstraint(
            "default_shelf_life_days IS NULL OR default_shelf_life_days >= 0",
            name="shelf_life_days",
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(200))
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    base_unit: Mapped[BaseUnit] = mapped_column(str_enum(BaseUnit, "base_unit"), nullable=False)
    # Mindest-/Zielbestand in der Basiseinheit; NULL = keine Überwachung (FR-SHP-001)
    minimum_stock: Mapped[Decimal | None] = mapped_column(QTY)
    target_stock: Mapped[Decimal | None] = mapped_column(QTY)
    default_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    default_shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    expiry_warning_days: Mapped[int | None] = mapped_column(Integer)
    image_path: Mapped[str | None] = mapped_column(String(255))
    image_source: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    category: Mapped[ProductCategory] = relationship(lazy="joined")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product",
        order_by="ProductVariant.base_quantity",
        lazy="selectin",
    )


class ProductVariant(UUIDPk, Timestamps, Base):
    """Verpackungsvariante, optional mit eigenem Barcode (Spezifikation 4.3)."""

    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("package_quantity > 0", name="package_quantity_positive"),
        CheckConstraint("base_quantity > 0", name="base_quantity_positive"),
        # Ein Barcode gehört innerhalb eines Haushalts zu genau einer Variante (FR-PRD-002).
        Index(
            "uq_product_variants_barcode",
            "household_id",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    barcode: Mapped[str | None] = mapped_column(String(32))
    package_quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    package_unit: Mapped[PackageUnit] = mapped_column(
        str_enum(PackageUnit, "package_unit"), nullable=False
    )
    # Menge in der Basiseinheit des Produkts, z. B. 1 kg → 1000
    base_quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")

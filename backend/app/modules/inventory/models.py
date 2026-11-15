"""Inventur (Spezifikation Kap. 8; DEC-019: lagerplatzweise und vollständig)."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk, str_enum
from app.modules.catalog.models import QTY, Product, ProductVariant
from app.modules.locations.models import Location
from app.modules.stock.models import ExpiryType, StockItem


class InventoryStatus(enum.StrEnum):
    OPEN = "open"  # begonnen, kann unterbrochen und fortgesetzt werden (FR-INV-006)
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Inventory(UUIDPk, Timestamps, Base):
    __tablename__ = "inventories"

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # NULL = gesamter Haushalt (FR-INV-001)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )
    include_sublocations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Beim Start festgehaltene Lagerplätze; Grundlage für Überschneidungsprüfung und Protokoll
    location_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    status: Mapped[InventoryStatus] = mapped_column(
        str_enum(InventoryStatus, "inventory_status"),
        nullable=False,
        default=InventoryStatus.OPEN,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    # Buchungsvorgang der Korrekturbuchungen (Historie)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column()

    location: Mapped[Location | None] = relationship(lazy="joined")
    items: Mapped[list["InventoryItem"]] = relationship(
        back_populates="inventory", lazy="selectin", cascade="all, delete-orphan"
    )


class InventoryItem(UUIDPk, Timestamps, Base):
    """Eine Zeile der Inventurliste: genau eine Bestandsposition (FR-INV-009) oder ein
    während der Inventur ergänztes Lebensmittel (FR-INV-005)."""

    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("expected_quantity >= 0", name="expected_non_negative"),
        CheckConstraint(
            "counted_quantity IS NULL OR counted_quantity >= 0", name="counted_non_negative"
        ),
        CheckConstraint("is_new = (stock_item_id IS NULL)", name="new_has_no_position"),
        CheckConstraint(
            "(expiry_type IN ('best_before', 'use_by')) = (expiry_date IS NOT NULL)",
            name="expiry_date_matches_type",
        ),
    )

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_items.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False
    )
    expiry_type: Mapped[ExpiryType] = mapped_column(
        str_enum(ExpiryType, "expiry_type"), nullable=False
    )
    expiry_date: Mapped[date | None] = mapped_column(Date)
    is_new: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Sollbestand und Version der Position beim Start bzw. bei der letzten Bestätigung;
    # weicht die Position davon ab, wurde zwischenzeitlich gebucht (FR-INV-008).
    expected_quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    expected_version: Mapped[int | None] = mapped_column(Integer)
    counted_quantity: Mapped[Decimal | None] = mapped_column(QTY)
    counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)
    # Beim Abschluss gebuchte Korrektur (Protokoll, FR-INV-007)
    applied_delta: Mapped[Decimal | None] = mapped_column(QTY)
    # Position, auf die eine Korrektur für ein ergänztes Lebensmittel gebucht wurde
    resulting_stock_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_items.id", ondelete="RESTRICT")
    )

    inventory: Mapped[Inventory] = relationship(back_populates="items")
    stock_item: Mapped[StockItem | None] = relationship(lazy="joined", foreign_keys=[stock_item_id])
    product: Mapped[Product] = relationship(lazy="joined")
    variant: Mapped[ProductVariant | None] = relationship(lazy="joined")
    location: Mapped[Location] = relationship(lazy="joined")

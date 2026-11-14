import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk, str_enum
from app.modules.catalog.models import QTY, Product, ProductVariant
from app.modules.locations.models import Location


class ExpiryType(enum.StrEnum):
    BEST_BEFORE = "best_before"  # Mindesthaltbarkeitsdatum
    USE_BY = "use_by"  # Verbrauchsdatum
    NONE = "none"  # Kein Haltbarkeitsdatum
    UNKNOWN = "unknown"  # Haltbarkeitsdatum unbekannt


class StockStatus(enum.StrEnum):
    AVAILABLE = "available"
    CONSUMED = "consumed"
    DISPOSED = "disposed"


class MovementType(enum.StrEnum):
    RECEIPT = "receipt"  # Einlagerung
    CONSUMPTION = "consumption"  # Verbrauch
    TRANSFER_OUT = "transfer_out"  # Umlagerung – Abgang
    TRANSFER_IN = "transfer_in"  # Umlagerung – Zugang
    INVENTORY_CORRECTION = "inventory_correction"
    DISPOSAL = "disposal"  # Entsorgung
    REVERSAL = "reversal"  # Stornierung / Gegenbuchung


class StockItem(UUIDPk, Timestamps, Base):
    """Bestandsposition: konkrete Menge an einem Lagerplatz mit einem Haltbarkeitsdatum."""

    __tablename__ = "stock_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint(
            "(expiry_type IN ('best_before', 'use_by')) = (expiry_date IS NOT NULL)",
            name="expiry_date_matches_type",
        ),
        Index("ix_stock_items_available", "household_id", "product_id", "status"),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    expiry_type: Mapped[ExpiryType] = mapped_column(
        str_enum(ExpiryType, "expiry_type"), nullable=False
    )
    received_on: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    opened_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[StockStatus] = mapped_column(
        str_enum(StockStatus, "stock_status"), nullable=False, default=StockStatus.AVAILABLE
    )
    note: Mapped[str | None] = mapped_column(Text)
    # Optimistisches Locking (Spezifikation 12.2)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012

    product: Mapped[Product] = relationship(lazy="joined")
    variant: Mapped[ProductVariant | None] = relationship(lazy="joined")
    location: Mapped[Location] = relationship(lazy="joined")


class StockMovement(UUIDPk, Base):
    """Unveränderliche Bestandsbewegung (Spezifikation 4.6, BR-006, BR-018)."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_stock_movements_created", "household_id", "created_at"),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    # Fasst zusammengehörige Bewegungen eines Vorgangs zusammen (z. B. Umlagerung)
    transaction_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    movement_type: Mapped[MovementType] = mapped_column(
        str_enum(MovementType, "movement_type"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stock_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )
    target_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT")
    )
    # Immer positiv; die Richtung ergibt sich aus movement_type bzw. quantity_delta
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    # Bestandsveränderung der Position (+ Zugang, − Abgang)
    quantity_delta: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(50))
    comment: Mapped[str | None] = mapped_column(Text)
    reverses_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class IdempotencyRecord(Base):
    """Gespeichertes Ergebnis einer Buchungsanfrage (DEC-025, BR-017, NFR-REL-002)."""

    __tablename__ = "idempotency_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

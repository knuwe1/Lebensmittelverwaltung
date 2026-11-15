"""Einkaufsliste (Spezifikation Kap. 6, 12.1; DEC-018: eine gemeinsame aktive Liste)."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk, str_enum
from app.modules.catalog.models import QTY, Product


class ItemOrigin(enum.StrEnum):
    AUTO = "auto"  # aus der Bedarfsermittlung
    MANUAL = "manual"  # vom Benutzer ergänzt (BR-020)


class ItemStatus(enum.StrEnum):
    OPEN = "open"  # noch zu kaufen
    PURCHASED = "purchased"  # gekauft, aber noch nicht eingelagert (BR-007)
    DONE = "done"  # eingelagert


class ShoppingList(UUIDPk, Timestamps, Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (
        # Genau eine aktive Liste je Haushalt (DEC-018)
        Index(
            "uq_shopping_lists_active",
            "household_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Einkaufsliste")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ShoppingListItem(UUIDPk, Timestamps, Base):
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        CheckConstraint("(product_id IS NOT NULL) <> (name IS NOT NULL)", name="product_or_name"),
        CheckConstraint("origin = 'manual' OR product_id IS NOT NULL", name="auto_has_product"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "suggested_quantity IS NULL OR suggested_quantity >= 0", name="suggested_non_negative"
        ),
        CheckConstraint("received_quantity >= 0", name="received_non_negative"),
        # Höchstens eine offene bzw. gekaufte automatische Position je Produkt (FR-SHP-010)
        Index(
            "uq_shopping_list_items_auto_product",
            "list_id",
            "product_id",
            unique=True,
            postgresql_where=text("origin = 'auto' AND status IN ('open', 'purchased')"),
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Entweder ein Produkt aus dem Katalog oder ein freier Text (nur manuell)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    origin: Mapped[ItemOrigin] = mapped_column(str_enum(ItemOrigin, "origin"), nullable=False)
    # Automatische Positionen nahe am Mindestbestand sind optional, bis sie übernommen werden
    optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[ItemStatus] = mapped_column(
        str_enum(ItemStatus, "shopping_item_status"), nullable=False, default=ItemStatus.OPEN
    )
    # Mengen in der Basiseinheit des Produkts; bei Freitext eine einfache Anzahl
    suggested_quantity: Mapped[Decimal | None] = mapped_column(QTY)
    quantity: Mapped[Decimal | None] = mapped_column(QTY)  # manuell angepasste Menge
    received_quantity: Mapped[Decimal] = mapped_column(
        QTY, nullable=False, default=Decimal(0), server_default=text("0")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    # Vom Benutzer bearbeitet: wird von der Bedarfsermittlung nicht mehr entfernt
    adjusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purchased_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    product: Mapped[Product | None] = relationship(lazy="joined")

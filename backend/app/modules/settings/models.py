import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps

DEFAULT_EXPIRY_WARNING_DAYS = 7  # DEC-017
DEFAULT_STOCK_WARNING_FACTOR = Decimal("1.25")  # DEC-016


class HouseholdSettings(Timestamps, Base):
    """Administrativ konfigurierbare Einstellungen eines Haushalts (Spez. 9.2 „Einstellungen“)."""

    __tablename__ = "household_settings"
    __table_args__ = (
        CheckConstraint("expiry_warning_days >= 0", name="expiry_warning_days"),
        CheckConstraint("stock_warning_factor >= 1", name="stock_warning_factor"),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
    # Barcode-Abfrage bei Open Food Facts (DEC-028). Standard aus: externe Übermittlung nur
    # nach bewusster Konfiguration (NFR-DAT-002).
    external_product_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Haltbarkeitswarnung in Tagen (FR-EXP-002, DEC-017)
    expiry_warning_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_EXPIRY_WARNING_DAYS,
        server_default=text(str(DEFAULT_EXPIRY_WARNING_DAYS)),
    )
    # Warnbereich = Mindestbestand × Faktor (FR-SHP-004, DEC-016)
    stock_warning_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=DEFAULT_STOCK_WARNING_FACTOR,
        server_default=text(str(DEFAULT_STOCK_WARNING_FACTOR)),
    )

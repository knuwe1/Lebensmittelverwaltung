import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk


class Location(UUIDPk, Timestamps, Base):
    """Hierarchischer Lagerplatz (Spezifikation 4.4). Die Tiefe ist nicht begrenzt."""

    __tablename__ = "locations"
    __table_args__ = (
        # Namen eindeutig innerhalb desselben übergeordneten Lagerplatzes (auch auf oberster Ebene)
        UniqueConstraint("household_id", "parent_id", "name", postgresql_nulls_not_distinct=True),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_type: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

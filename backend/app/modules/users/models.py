import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk


class Role(enum.StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class Household(UUIDPk, Timestamps, Base):
    """Ein Haushalt. Im MVP existiert genau einer (DEC-002); das Modell erlaubt später mehrere."""

    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(200), nullable=False)


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=Role.MEMBER,
    )
    # Haushaltsmitglieder dürfen Inventuren nur durchführen, wenn freigegeben (Spez. 3.1).
    can_do_inventory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Wird bei Passwortänderung/Deaktivierung erhöht und macht bestehende Sitzungen ungültig.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    household: Mapped[Household] = relationship(lazy="joined")

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def may_do_inventory(self) -> bool:
        return self.is_admin or self.can_do_inventory

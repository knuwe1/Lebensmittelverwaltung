"""Importiert sämtliche ORM-Modelle, damit Alembic und Tests die vollständigen Metadaten sehen."""

from app.db.base import Base
from app.modules.users.models import Household, User

__all__ = ["Base", "Household", "User"]

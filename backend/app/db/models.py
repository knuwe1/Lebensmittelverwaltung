"""Importiert sämtliche ORM-Modelle, damit Alembic und Tests die vollständigen Metadaten sehen."""

from app.db.base import Base
from app.modules.catalog.models import Product, ProductCategory, ProductVariant
from app.modules.locations.models import Location
from app.modules.stock.models import IdempotencyRecord, StockItem, StockMovement
from app.modules.users.models import Household, User

__all__ = [
    "Base",
    "Household",
    "IdempotencyRecord",
    "Location",
    "Product",
    "ProductCategory",
    "ProductVariant",
    "StockItem",
    "StockMovement",
    "User",
]

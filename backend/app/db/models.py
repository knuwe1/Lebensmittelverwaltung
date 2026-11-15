"""Importiert sämtliche ORM-Modelle, damit Alembic und Tests die vollständigen Metadaten sehen."""

from app.db.base import Base
from app.modules.catalog.models import Product, ProductCategory, ProductVariant
from app.modules.inventory.models import Inventory, InventoryItem
from app.modules.locations.models import Location
from app.modules.settings.models import HouseholdSettings
from app.modules.shopping.models import ShoppingList, ShoppingListItem
from app.modules.stock.models import IdempotencyRecord, StockItem, StockMovement
from app.modules.users.models import Household, User

__all__ = [
    "Base",
    "Household",
    "HouseholdSettings",
    "IdempotencyRecord",
    "Inventory",
    "InventoryItem",
    "Location",
    "Product",
    "ProductCategory",
    "ProductVariant",
    "ShoppingList",
    "ShoppingListItem",
    "StockItem",
    "StockMovement",
    "User",
]

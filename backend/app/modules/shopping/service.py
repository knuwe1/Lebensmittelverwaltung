"""Einkaufsliste (FR-SHP-005…010, BR-007, BR-020, DEC-018)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailed
from app.core.units import normalize
from app.modules.catalog import service as catalog
from app.modules.catalog.models import Product, ProductVariant
from app.modules.shopping.models import ItemOrigin, ItemStatus, ShoppingList, ShoppingListItem
from app.modules.shopping.schemas import (
    PackageInfo,
    RefreshResult,
    ShoppingItemCreate,
    ShoppingItemOut,
    ShoppingItemUpdate,
    ShoppingListOut,
)
from app.modules.stock import service as stock
from app.modules.stock.schemas import StockLevelOut
from app.modules.stock.status import StockLevelStatus, restock_quantity
from app.modules.users.models import User

ACTIVE_STATUSES = (ItemStatus.OPEN, ItemStatus.PURCHASED)
NEED_STATUSES = (StockLevelStatus.BELOW, StockLevelStatus.AT_MINIMUM, StockLevelStatus.NEAR)
STATUS_ORDER = {ItemStatus.OPEN: 0, ItemStatus.PURCHASED: 1, ItemStatus.DONE: 2}


def active_list(db: Session, household_id: uuid.UUID) -> ShoppingList:
    """Die gemeinsame aktive Liste des Haushalts; wird bei Bedarf angelegt (DEC-018)."""
    lst = db.scalar(
        select(ShoppingList).where(
            ShoppingList.household_id == household_id, ShoppingList.active.is_(True)
        )
    )
    if lst is None:
        db.execute(
            insert(ShoppingList)
            .values(id=uuid.uuid4(), household_id=household_id, name="Einkaufsliste", active=True)
            .on_conflict_do_nothing(index_elements=["household_id"], index_where=text("active"))
        )
        db.flush()
        lst = db.scalar(
            select(ShoppingList).where(
                ShoppingList.household_id == household_id, ShoppingList.active.is_(True)
            )
        )
    return lst


def _lock(db: Session, lst: ShoppingList) -> None:
    """Serialisiert Bedarfsermittlung und Ergänzungen einer Liste (keine Doppelpositionen)."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"shopping:{lst.id}"})


def default_variant(product: Product) -> ProductVariant | None:
    return next((v for v in product.variants if v.active and v.is_default), None)


def _item_out(item: ShoppingListItem, levels: dict[uuid.UUID, StockLevelOut]) -> ShoppingItemOut:
    product = item.product
    quantity = item.quantity if item.quantity is not None else item.suggested_quantity
    variant = default_variant(product) if product else None
    package = packages = None
    if variant:
        package = PackageInfo(
            variant_id=variant.id,
            package_quantity=variant.package_quantity,
            package_unit=variant.package_unit,
            base_quantity=variant.base_quantity,
            name=variant.name,
        )
        if quantity is not None and quantity % variant.base_quantity == 0:
            packages = normalize(quantity / variant.base_quantity)
    level = levels.get(item.product_id) if item.product_id else None
    return ShoppingItemOut(
        id=item.id,
        origin=item.origin,
        optional=item.optional,
        status=item.status,
        product_id=item.product_id,
        name=product.name if product else item.name,
        brand=product.brand if product else None,
        category_name=product.category.name if product else None,
        base_unit=product.base_unit if product else None,
        suggested_quantity=item.suggested_quantity,
        quantity=quantity,
        quantity_adjusted=item.quantity is not None,
        package=package,
        packages=packages,
        received_quantity=item.received_quantity,
        comment=item.comment,
        available_quantity=level.available_quantity if level else None,
        minimum_stock=product.minimum_stock if product else None,
        target_stock=product.target_stock if product else None,
        level_status=level.status if level else None,
        purchased_at=item.purchased_at,
        created_at=item.created_at,
    )


def list_out(
    db: Session, household_id: uuid.UUID, lst: ShoppingList | None = None
) -> ShoppingListOut:
    lst = lst or active_list(db, household_id)
    items = db.scalars(select(ShoppingListItem).where(ShoppingListItem.list_id == lst.id)).all()
    levels = {lvl.product_id: lvl for lvl in stock.stock_levels(db, household_id)}
    out = [_item_out(i, levels) for i in items]
    # Offen vor gekauft vor erledigt; innerhalb nach Produktgruppe (Laufweg im Laden) und Name
    out.sort(key=lambda o: (STATUS_ORDER[o.status], o.category_name or "~", o.name.lower()))
    return ShoppingListOut(id=lst.id, name=lst.name, items=out)


def get_item(db: Session, household_id: uuid.UUID, item_id: uuid.UUID) -> ShoppingListItem:
    item = db.get(ShoppingListItem, item_id)
    if item is None or item.household_id != household_id:
        raise NotFoundError("Position nicht gefunden.", code="shopping_item_not_found")
    return item


def refresh(db: Session, user: User) -> RefreshResult:
    """Bedarfsermittlung (FR-SHP-005/010): erzeugt bzw. aktualisiert automatische Positionen,
    ohne Duplikate. Manuelle, gekaufte und vom Benutzer bearbeitete Positionen bleiben
    unangetastet; automatische, deren Bedarf entfallen ist, werden entfernt."""
    lst = active_list(db, user.household_id)
    _lock(db, lst)
    levels = stock.stock_levels(db, user.household_id, NEED_STATUSES)
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_([lv.product_id for lv in levels])))
    }
    items = db.scalars(
        select(ShoppingListItem).where(
            ShoppingListItem.list_id == lst.id,
            ShoppingListItem.status.in_(ACTIVE_STATUSES),
            ShoppingListItem.product_id.is_not(None),
        )
    ).all()
    auto = {i.product_id: i for i in items if i.origin == ItemOrigin.AUTO}
    manual = {i.product_id for i in items if i.origin == ItemOrigin.MANUAL}

    added = updated = removed = 0
    needed: set[uuid.UUID] = set()
    for level in levels:
        needed.add(level.product_id)
        if level.product_id in manual:
            continue  # bereits manuell auf der Liste
        existing = auto.get(level.product_id)
        if existing is not None and existing.status == ItemStatus.PURCHASED:
            continue  # gekauft, aber noch nicht eingelagert – nicht erneut vorschlagen
        variant = default_variant(products[level.product_id])
        suggestion = restock_quantity(
            level.available_quantity,
            level.minimum_stock,
            level.target_stock,
            variant.base_quantity if variant else None,
        )
        optional = level.status == StockLevelStatus.NEAR
        if existing is None:
            db.add(
                ShoppingListItem(
                    household_id=user.household_id,
                    list_id=lst.id,
                    product_id=level.product_id,
                    origin=ItemOrigin.AUTO,
                    optional=optional,
                    suggested_quantity=suggestion,
                    created_by=user.id,
                )
            )
            added += 1
            continue
        changed = existing.suggested_quantity != suggestion
        existing.suggested_quantity = suggestion
        # Eine übernommene optionale Position bleibt übernommen; dringender Bedarf hebt
        # die Kennzeichnung „optional“ immer auf.
        if existing.optional and (not optional):
            existing.optional, changed = False, True
        elif not existing.adjusted and existing.optional != optional:
            existing.optional, changed = optional, True
        updated += changed

    for product_id, item in auto.items():
        if product_id not in needed and item.status == ItemStatus.OPEN and not item.adjusted:
            db.delete(item)
            removed += 1
    db.flush()
    return RefreshResult(
        added=added, updated=updated, removed=removed, list=list_out(db, user.household_id, lst)
    )


def add_item(db: Session, user: User, data: ShoppingItemCreate) -> ShoppingItemOut:
    """Manuelle Position (FR-SHP-007). Steht das Produkt schon offen auf der Liste, wird
    diese Position übernommen statt eine zweite anzulegen."""
    lst = active_list(db, user.household_id)
    _lock(db, lst)
    item = None
    if data.product_id:
        product = catalog.get_product(db, user.household_id, data.product_id)
        if not product.active:
            raise ValidationFailed("Das Produkt ist deaktiviert.", code="product_inactive")
        item = db.scalar(
            select(ShoppingListItem).where(
                ShoppingListItem.list_id == lst.id,
                ShoppingListItem.product_id == product.id,
                ShoppingListItem.status == ItemStatus.OPEN,
            )
        )
    if item is None:
        item = ShoppingListItem(
            household_id=user.household_id,
            list_id=lst.id,
            product_id=data.product_id,
            name=None if data.product_id else data.name,
            origin=ItemOrigin.MANUAL,
            created_by=user.id,
        )
        db.add(item)
    item.optional = False
    item.adjusted = True
    if data.quantity is not None:
        item.quantity = data.quantity
    if data.comment is not None:
        item.comment = data.comment or None
    db.flush()
    db.refresh(item)
    return item_out(db, user.household_id, item)


def item_out(db: Session, household_id: uuid.UUID, item: ShoppingListItem) -> ShoppingItemOut:
    levels = {}
    if item.product_id:
        levels = {lv.product_id: lv for lv in stock.stock_levels(db, household_id)}
    return _item_out(item, levels)


def update_item(
    db: Session, user: User, item_id: uuid.UUID, data: ShoppingItemUpdate
) -> ShoppingItemOut:
    """Menge, Kommentar, Übernahme optionaler Positionen, Status (FR-SHP-007/008).
    „Gekauft“ ändert den Bestand nicht (BR-007)."""
    item = get_item(db, user.household_id, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "quantity" in changes:
        item.quantity = data.quantity
        item.adjusted = True
    if "comment" in changes:
        item.comment = data.comment or None
        item.adjusted = True
    if data.optional is False and item.optional:
        item.optional = False
        item.adjusted = True
    if data.status is not None:
        _set_status(item, ItemStatus(data.status.value), user)
    db.flush()
    db.refresh(item)
    return item_out(db, user.household_id, item)


def _set_status(item: ShoppingListItem, status: ItemStatus, user: User) -> None:
    if status == item.status:
        return
    if status == ItemStatus.PURCHASED:
        item.purchased_at, item.purchased_by = datetime.now(UTC), user.id
    elif status == ItemStatus.OPEN:
        if item.origin == ItemOrigin.AUTO and item.status == ItemStatus.DONE:
            # Eine erledigte automatische Position würde die Eindeutigkeit verletzen,
            # falls inzwischen eine neue offene existiert – dann lieber neu ermitteln lassen.
            raise ValidationFailed(
                "Erledigte Vorschläge lassen sich nicht wieder öffnen. Bitte Bedarf neu ermitteln.",
                code="cannot_reopen",
            )
        item.purchased_at = item.purchased_by = None
    item.status = status


def delete_item(db: Session, user: User, item_id: uuid.UUID) -> None:
    db.delete(get_item(db, user.household_id, item_id))
    db.flush()


def clear_done(db: Session, user: User) -> ShoppingListOut:
    lst = active_list(db, user.household_id)
    for item in db.scalars(
        select(ShoppingListItem).where(
            ShoppingListItem.list_id == lst.id, ShoppingListItem.status == ItemStatus.DONE
        )
    ):
        db.delete(item)
    db.flush()
    return list_out(db, user.household_id, lst)


def record_receipt(
    db: Session, user: User, item_id: uuid.UUID, product_id: uuid.UUID, quantity: Decimal
) -> None:
    """Einlagerung aus der Einkaufsliste (FR-SHP-009): Erst die bestätigte Einlagerung erhöht
    den Bestand (BR-008); die Position wird in derselben Transaktion als erledigt markiert."""
    item = get_item(db, user.household_id, item_id)
    if item.product_id != product_id:
        raise ValidationFailed(
            "Die Position gehört zu einem anderen Lebensmittel.", code="shopping_item_mismatch"
        )
    if item.status == ItemStatus.DONE:
        raise ValidationFailed("Die Position wurde bereits eingelagert.", code="shopping_item_done")
    item.received_quantity = normalize(item.received_quantity + quantity)
    if item.purchased_at is None:
        item.purchased_at, item.purchased_by = datetime.now(UTC), user.id
    item.status = ItemStatus.DONE

"""Inventur und Bestandskorrekturen (FR-INV-001…009, DEC-019)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.units import normalize
from app.modules.catalog import service as catalog
from app.modules.inventory.models import Inventory, InventoryItem, InventoryStatus
from app.modules.inventory.schemas import (
    CountUpdate,
    InventoryConflict,
    InventoryCreate,
    InventoryItemCreate,
    InventoryItemOut,
    InventoryOut,
    InventorySummary,
)
from app.modules.locations import service as locations
from app.modules.stock.models import MovementType, StockItem, StockStatus
from app.modules.stock.service import _record, location_paths, lock_product
from app.modules.users.models import User

REASON_CHANGED = "Seit dem Start wurde auf diese Position gebucht – bitte erneut zählen."
REASON_NEW = "Seit dem Start neu eingelagert – bitte zählen."


def _now() -> datetime:
    return datetime.now(UTC)


def _lock_household(db: Session, household_id: uuid.UUID) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"inventory:{household_id}"}
    )


def get_inventory(db: Session, household_id: uuid.UUID, inventory_id: uuid.UUID) -> Inventory:
    inv = db.get(Inventory, inventory_id)
    if inv is None or inv.household_id != household_id:
        raise NotFoundError("Inventur nicht gefunden.", code="inventory_not_found")
    return inv


def _open_inventory(db: Session, household_id: uuid.UUID, inventory_id: uuid.UUID) -> Inventory:
    inv = get_inventory(db, household_id, inventory_id)
    if inv.status != InventoryStatus.OPEN:
        raise ValidationFailed("Die Inventur ist bereits beendet.", code="inventory_closed")
    return inv


def _get_item(inv: Inventory, item_id: uuid.UUID) -> InventoryItem:
    item = next((i for i in inv.items if i.id == item_id), None)
    if item is None:
        raise NotFoundError("Position nicht gefunden.", code="inventory_item_not_found")
    return item


# ------------------------------------------------------------------ Ausgabe


def _current(item: InventoryItem) -> tuple[Decimal | None, bool]:
    """Aktueller Buchbestand und ob er vom festgehaltenen Soll abweicht (FR-INV-008)."""
    if item.is_new or item.stock_item is None:
        return None, False
    stock = item.stock_item
    current = stock.quantity if stock.status == StockStatus.AVAILABLE else Decimal(0)
    return current, stock.version != item.expected_version


def _item_out(item: InventoryItem, paths: dict[uuid.UUID, str]) -> InventoryItemOut:
    current, conflict = _current(item)
    conflict = conflict and item.inventory.status == InventoryStatus.OPEN
    reason = None
    if conflict:
        reason = "new" if item.expected_version is None else "changed"
    counted = item.counted_quantity
    return InventoryItemOut(
        id=item.id,
        stock_item_id=item.stock_item_id,
        is_new=item.is_new,
        product_id=item.product_id,
        product_name=item.product.name,
        product_brand=item.product.brand,
        base_unit=item.product.base_unit,
        variant_id=item.variant_id,
        location_id=item.location_id,
        location_path=paths.get(item.location_id, item.location.name),
        expiry_type=item.expiry_type,
        expiry_date=item.expiry_date,
        expected_quantity=item.expected_quantity,
        counted_quantity=counted,
        difference=None if counted is None else normalize(counted - item.expected_quantity),
        current_quantity=current,
        conflict=conflict,
        conflict_reason=reason,
        note=item.note,
        counted_at=item.counted_at,
        applied_delta=item.applied_delta,
    )


def _user_name(db: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user.display_name if user else None


def inventory_out(db: Session, inv: Inventory, *, with_items: bool = True) -> InventoryOut:
    paths = location_paths(db, inv.household_id)
    items = [_item_out(i, paths) for i in inv.items]
    items.sort(
        key=lambda i: (i.location_path.lower(), i.product_name.lower(), i.expiry_date or date.max)
    )
    if inv.location_id is None:
        scope = "Gesamter Haushalt"
    else:
        scope = paths.get(inv.location_id, inv.location.name)
        if inv.include_sublocations and len(inv.location_ids) > 1:
            scope += " (mit Unterlagerplätzen)"
    return InventoryOut(
        id=inv.id,
        status=inv.status,
        location_id=inv.location_id,
        scope_label=scope,
        include_sublocations=inv.include_sublocations,
        location_ids=list(inv.location_ids),
        location_paths=sorted(paths.get(lid, "?") for lid in inv.location_ids),
        note=inv.note,
        started_at=inv.started_at,
        started_by_name=_user_name(db, inv.started_by) or "?",
        completed_at=inv.completed_at,
        completed_by_name=_user_name(db, inv.completed_by),
        transaction_id=inv.transaction_id,
        summary=InventorySummary(
            total=len(items),
            counted=sum(i.counted_quantity is not None for i in items),
            differences=sum(
                (i.applied_delta if inv.status == InventoryStatus.COMPLETED else i.difference)
                not in (None, 0)
                for i in items
            ),
            conflicts=sum(i.conflict for i in items),
        ),
        items=items if with_items else None,
    )


def list_inventories(db: Session, household_id: uuid.UUID) -> list[InventoryOut]:
    invs = db.scalars(
        select(Inventory)
        .where(Inventory.household_id == household_id)
        .order_by(Inventory.started_at.desc())
    ).all()
    return [inventory_out(db, i, with_items=False) for i in invs]


# ------------------------------------------------------------------ Ablauf


def _available_in(db: Session, household_id: uuid.UUID, location_ids: list[uuid.UUID]):
    return db.scalars(
        select(StockItem).where(
            StockItem.household_id == household_id,
            StockItem.status == StockStatus.AVAILABLE,
            StockItem.location_id.in_(location_ids),
        )
    ).all()


def _snapshot_item(stock: StockItem) -> InventoryItem:
    return InventoryItem(
        stock_item_id=stock.id,
        product_id=stock.product_id,
        variant_id=stock.variant_id,
        location_id=stock.location_id,
        expiry_type=stock.expiry_type,
        expiry_date=stock.expiry_date,
        expected_quantity=stock.quantity,
        expected_version=stock.version,
    )


def start(db: Session, user: User, data: InventoryCreate) -> Inventory:
    """Inventur starten (FR-INV-001/002): hält die aktuellen Bestandspositionen als Soll fest.
    Überschneidende offene Inventuren sind nicht erlaubt."""
    _lock_household(db, user.household_id)
    if data.location_id is None:
        ids = [
            loc.id for loc in locations.list_locations(db, user.household_id, include_inactive=True)
        ]
    else:
        locations.get_location(db, user.household_id, data.location_id)
        ids = (
            locations.subtree_ids(db, user.household_id, data.location_id)
            if data.include_sublocations
            else [data.location_id]
        )
    if not ids:
        raise ValidationFailed("Es sind noch keine Lagerplätze angelegt.", code="no_locations")
    overlapping = db.scalar(
        select(Inventory).where(
            Inventory.household_id == user.household_id,
            Inventory.status == InventoryStatus.OPEN,
            Inventory.location_ids.overlap(ids),
        )
    )
    if overlapping is not None:
        raise ConflictError(
            "Für diese Lagerplätze läuft bereits eine Inventur. Bitte diese fortsetzen oder "
            "abbrechen.",
            code="inventory_overlap",
            details={"inventory_id": str(overlapping.id)},
        )
    inv = Inventory(
        household_id=user.household_id,
        location_id=data.location_id,
        include_sublocations=data.include_sublocations if data.location_id else True,
        location_ids=ids,
        note=data.note,
        started_by=user.id,
    )
    inv.items = [_snapshot_item(s) for s in _available_in(db, user.household_id, ids)]
    db.add(inv)
    db.flush()
    return inv


def count(
    db: Session, user: User, inventory_id: uuid.UUID, item_id: uuid.UUID, data: CountUpdate
) -> Inventory:
    """Istbestand erfassen (FR-INV-002). `null` setzt die Zählung zurück."""
    inv = _open_inventory(db, user.household_id, inventory_id)
    item = _get_item(inv, item_id)
    if item.is_new and data.counted_quantity is not None and data.counted_quantity <= 0:
        raise ValidationFailed(
            "Ergänzte Lebensmittel brauchen eine Menge größer als null – sonst entfernen.",
            code="invalid_quantity",
        )
    current, conflict = _current(item)
    if conflict and data.counted_quantity is not None:
        # Erneut geprüft: aktueller Buchbestand wird neues Soll (FR-INV-008)
        item.expected_quantity = current
        item.expected_version = item.stock_item.version
    item.counted_quantity = data.counted_quantity
    item.counted_at = _now() if data.counted_quantity is not None else None
    item.counted_by = user.id if data.counted_quantity is not None else None
    if "note" in data.model_fields_set:
        item.note = data.note or None
    db.flush()
    return inv


def add_item(
    db: Session, user: User, inventory_id: uuid.UUID, data: InventoryItemCreate
) -> Inventory:
    """Nicht erfasstes Lebensmittel ergänzen (FR-INV-005); gebucht wird erst beim Abschluss."""
    inv = _open_inventory(db, user.household_id, inventory_id)
    product = catalog.get_product(db, user.household_id, data.product_id)
    if not product.active:
        raise ValidationFailed("Das Produkt ist deaktiviert.", code="product_inactive")
    if data.variant_id:
        catalog.get_variant(db, product, data.variant_id)
    if data.location_id not in inv.location_ids:
        raise ValidationFailed(
            "Der Lagerplatz gehört nicht zu dieser Inventur.", code="location_not_in_inventory"
        )
    locations.get_active_location(db, user.household_id, data.location_id)
    inv.items.append(
        InventoryItem(
            stock_item_id=None,
            is_new=True,
            product_id=product.id,
            variant_id=data.variant_id,
            location_id=data.location_id,
            expiry_type=data.expiry_type,
            expiry_date=data.expiry_date,
            expected_quantity=Decimal(0),
            counted_quantity=data.counted_quantity,
            counted_at=_now(),
            counted_by=user.id,
            note=data.note,
        )
    )
    db.flush()
    return inv


def remove_item(db: Session, user: User, inventory_id: uuid.UUID, item_id: uuid.UUID) -> Inventory:
    inv = _open_inventory(db, user.household_id, inventory_id)
    item = _get_item(inv, item_id)
    if not item.is_new:
        raise ValidationFailed(
            "Nur ergänzte Lebensmittel lassen sich entfernen. Nicht mehr vorhandene Bestände "
            "mit 0 zählen.",
            code="cannot_remove_item",
        )
    inv.items.remove(item)
    db.flush()
    return inv


def accept_remaining(db: Session, user: User, inventory_id: uuid.UUID) -> Inventory:
    """Alle noch nicht gezählten, unveränderten Positionen mit dem Soll übernehmen."""
    inv = _open_inventory(db, user.household_id, inventory_id)
    now = _now()
    for item in inv.items:
        if item.counted_quantity is None and not _current(item)[1]:
            item.counted_quantity, item.counted_at, item.counted_by = (
                item.expected_quantity,
                now,
                user.id,
            )
    db.flush()
    return inv


def cancel(db: Session, user: User, inventory_id: uuid.UUID) -> Inventory:
    inv = _open_inventory(db, user.household_id, inventory_id)
    inv.status = InventoryStatus.CANCELLED
    inv.completed_at, inv.completed_by = _now(), user.id
    db.flush()
    return inv


def sync(db: Session, inv: Inventory) -> list[InventoryConflict]:
    """Prüft auf zwischenzeitliche Buchungen (FR-INV-008): geänderte Positionen und seit dem
    Start neu entstandene Positionen im Inventurbereich. Neue werden der Liste hinzugefügt."""
    paths = location_paths(db, inv.household_id)
    known = {i.stock_item_id for i in inv.items if i.stock_item_id}
    for stock in _available_in(db, inv.household_id, inv.location_ids):
        if stock.id not in known:
            item = _snapshot_item(stock)
            item.expected_version = None  # erzwingt eine Zählung als neue Position
            inv.items.append(item)
    db.flush()
    conflicts = []
    for item in inv.items:
        if item.stock_item_id is None:
            continue
        if item.expected_version is None and item.counted_quantity is None:
            reason = REASON_NEW
        elif _current(item)[1] and item.expected_version is not None:
            reason = REASON_CHANGED
        else:
            continue
        conflicts.append(
            InventoryConflict(
                item_id=item.id,
                product_name=item.product.name,
                location_path=paths.get(item.location_id, item.location.name),
                reason=reason,
            )
        )
    return conflicts


def complete(db: Session, user: User, inventory_id: uuid.UUID) -> Inventory:
    """Inventur abschließen (FR-INV-004): bucht für jede Abweichung eine Korrektur. Bei
    zwischenzeitlichen Buchungen wird abgebrochen (FR-INV-008)."""
    inv = _open_inventory(db, user.household_id, inventory_id)
    for product_id in sorted({i.product_id for i in inv.items}, key=str):
        lock_product(db, product_id)
    db.refresh(inv)
    for item in inv.items:
        if item.stock_item is not None:
            db.refresh(item.stock_item)
    conflicts = sync(db, inv)
    if conflicts:
        raise ConflictError(
            "Seit dem Start der Inventur wurde gebucht. Bitte die markierten Positionen "
            "erneut prüfen.",
            code="inventory_conflict",
            details=[c.model_dump(mode="json") for c in conflicts],
        )
    uncounted = [i for i in inv.items if i.counted_quantity is None]
    if uncounted:
        raise ValidationFailed(
            f"{len(uncounted)} Position(en) sind noch nicht gezählt.",
            code="inventory_incomplete",
        )

    transaction_id = uuid.uuid4()
    comment = f"Inventur vom {inv.started_at.astimezone().strftime('%d.%m.%Y')}"
    for item in inv.items:
        if item.is_new:
            _book_new(db, user, inv, item, transaction_id, comment)
            continue
        stock = item.stock_item
        delta = normalize(item.counted_quantity - stock.quantity)
        item.applied_delta = delta
        if delta == 0:
            continue
        stock.quantity = normalize(item.counted_quantity)
        stock.status = StockStatus.AVAILABLE if stock.quantity > 0 else StockStatus.CONSUMED
        _record(
            db,
            user,
            stock,
            transaction_id=transaction_id,
            movement_type=MovementType.INVENTORY_CORRECTION,
            source_location_id=stock.location_id if delta < 0 else None,
            target_location_id=stock.location_id if delta > 0 else None,
            quantity=abs(delta),
            quantity_delta=delta,
            reason="inventory",
            comment=comment,
        )
    inv.status = InventoryStatus.COMPLETED
    inv.completed_at, inv.completed_by = _now(), user.id
    inv.transaction_id = transaction_id
    db.flush()
    return inv


def _book_new(
    db: Session,
    user: User,
    inv: Inventory,
    item: InventoryItem,
    transaction_id: uuid.UUID,
    comment: str,
) -> None:
    """Ergänztes Lebensmittel einbuchen (FR-INV-005); gleiche Merkmale → bestehende Position."""
    qty = normalize(item.counted_quantity)
    stock = db.scalar(
        select(StockItem)
        .where(
            StockItem.household_id == inv.household_id,
            StockItem.product_id == item.product_id,
            StockItem.variant_id.is_(None)
            if item.variant_id is None
            else StockItem.variant_id == item.variant_id,
            StockItem.location_id == item.location_id,
            StockItem.expiry_type == item.expiry_type,
            StockItem.expiry_date.is_(None)
            if item.expiry_date is None
            else StockItem.expiry_date == item.expiry_date,
            StockItem.opened_on.is_(None),
            StockItem.status == StockStatus.AVAILABLE,
        )
        .limit(1)
        .with_for_update(of=StockItem)
    )
    if stock is None:
        stock = StockItem(
            household_id=inv.household_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=item.location_id,
            quantity=qty,
            expiry_type=item.expiry_type,
            expiry_date=item.expiry_date,
            received_on=date.today(),
        )
        db.add(stock)
    else:
        stock.quantity = normalize(stock.quantity + qty)
    db.flush()
    item.applied_delta = qty
    item.resulting_stock_item_id = stock.id
    _record(
        db,
        user,
        stock,
        transaction_id=transaction_id,
        movement_type=MovementType.INVENTORY_CORRECTION,
        target_location_id=item.location_id,
        quantity=qty,
        quantity_delta=qty,
        reason="inventory",
        comment=comment,
    )

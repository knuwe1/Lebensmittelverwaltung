"""Entnahme, Entsorgung, Umlagerung und Storno (Phase 3).

Gemeinsame Regeln aller Buchungen:
- Produktsperre (``lock_product``) serialisiert Buchungen je Produkt (BR-015, BR-016).
- ``expected_version`` deckt zwischenzeitliche Änderungen auf (AC-012, AC-014).
- Bestände werden nie negativ (BR-004, FR-CNS-006); Fehler rollen die gesamte Buchung zurück.
- Jede Veränderung erzeugt eine unveränderliche Bewegung (BR-006, BR-018).
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.units import BaseUnit, normalize
from app.modules.catalog import service as catalog
from app.modules.catalog.models import Product
from app.modules.locations import service as locations
from app.modules.stock.fefo import plan_consumption
from app.modules.stock.models import MovementType, StockItem, StockMovement, StockStatus
from app.modules.stock.schemas import (
    AllocationIn,
    BookingResult,
    ConsumptionCreate,
    ConsumptionPlan,
    DisposalCreate,
    LineUnit,
    MovementOut,
    PlannedAllocation,
    ReversalCreate,
    TransferCreate,
    WeighingCreate,
    WeighingPreview,
)
from app.modules.stock.service import (
    _record,
    item_context,
    item_out,
    location_paths,
    lock_product,
)
from app.modules.stock.weighing import compute_weighing
from app.modules.users.models import User


class InsufficientStock(ConflictError):
    code = "insufficient_stock"


class StockChanged(ConflictError):
    code = "stock_changed"


def _available_items(db: Session, user: User, product_id: uuid.UUID, location_id=None):
    stmt = select(StockItem).where(
        StockItem.household_id == user.household_id,
        StockItem.product_id == product_id,
        StockItem.status == StockStatus.AVAILABLE,
        StockItem.quantity > 0,
    )
    if location_id:
        stmt = stmt.where(
            StockItem.location_id.in_(locations.subtree_ids(db, user.household_id, location_id))
        )
    return list(db.scalars(stmt))


def _requested_base_quantity(db: Session, product: Product, quantity, unit, variant_id) -> Decimal:
    if unit == LineUnit.PACKAGE:
        if not variant_id:
            raise ValidationFailed(
                "Für die Angabe in Packungen muss eine Variante gewählt werden.",
                code="variant_required",
            )
        variant = catalog.get_variant(db, product, variant_id)
        return normalize(quantity * variant.base_quantity)
    return normalize(quantity)


def consumption_plan(
    db: Session, user: User, product_id, quantity, unit, variant_id=None, location_id=None
) -> ConsumptionPlan:
    """FEFO-Vorschlag für eine Entnahme (FR-CNS-002, -003, -005). Bucht nichts."""
    product = catalog.get_product(db, user.household_id, product_id)
    requested = _requested_base_quantity(db, product, quantity, unit, variant_id)
    plan = plan_consumption(
        _available_items(db, user, product.id, location_id), requested, date.today()
    )
    ctx = item_context(db, user.household_id)
    return ConsumptionPlan(
        allocations=[
            PlannedAllocation(stock_item=item_out(a.position, ctx), quantity=a.quantity)
            for a in plan.allocations
        ],
        requested=requested,
        available=plan.available,
        sufficient=plan.sufficient,
    )


def _load_for_update(db: Session, user: User, product_id, alloc: AllocationIn) -> StockItem:
    item = db.scalar(
        select(StockItem)
        .where(StockItem.id == alloc.stock_item_id, StockItem.household_id == user.household_id)
        .with_for_update(of=StockItem)
        .execution_options(populate_existing=True)
    )
    if item is None or item.product_id != product_id:
        raise NotFoundError("Bestandsposition nicht gefunden.", code="stock_item_not_found")
    if alloc.expected_version is not None and item.version != alloc.expected_version:
        raise StockChanged(
            "Der Bestand wurde zwischenzeitlich von jemand anderem geändert. "
            "Bitte die Anzeige aktualisieren und die Buchung prüfen.",
            details={"stock_item_id": str(item.id), "quantity": float(item.quantity)},
        )
    if item.status != StockStatus.AVAILABLE or alloc.quantity > item.quantity:
        raise InsufficientStock(
            "Die Menge übersteigt den vorhandenen Bestand dieser Position.",
            details={
                "stock_item_id": str(item.id),
                "available": float(item.quantity if item.status == StockStatus.AVAILABLE else 0),
            },
        )
    return item


def _take(
    db: Session,
    user: User,
    product: Product,
    allocations: list[AllocationIn],
    movement_type: MovementType,
    emptied_status: StockStatus,
    reason: str | None,
    comment: str | None,
) -> BookingResult:
    if len({a.stock_item_id for a in allocations}) != len(allocations):
        raise ValidationFailed(
            "Eine Position wurde mehrfach angegeben.", code="duplicate_allocation"
        )
    lock_product(db, product.id)
    transaction_id = uuid.uuid4()
    touched: list[StockItem] = []
    total = Decimal(0)
    for alloc in allocations:
        item = _load_for_update(db, user, product.id, alloc)
        qty = normalize(alloc.quantity)
        item.quantity = normalize(item.quantity - qty)
        if item.quantity == 0:
            item.status = emptied_status
        _record(
            db,
            user,
            item,
            transaction_id=transaction_id,
            movement_type=movement_type,
            source_location_id=item.location_id,
            quantity=qty,
            quantity_delta=-qty,
            reason=reason,
            comment=comment,
        )
        touched.append(item)
        total += qty
    db.flush()
    ctx = item_context(db, user.household_id)
    return BookingResult(
        transaction_id=transaction_id,
        product=catalog.product_out(db, product),
        stock_items=[item_out(i, ctx) for i in touched],
        quantity=total,
    )


def book_consumption(db: Session, user: User, data: ConsumptionCreate) -> BookingResult:
    """Verbrauch (FR-CNS-001…006). Ohne explizite Positionen wird nach FEFO verteilt."""
    product = catalog.get_product(db, user.household_id, data.product_id)
    allocations = data.allocations
    if allocations is None:
        lock_product(db, product.id)  # Plan und Buchung unter derselben Sperre
        requested = _requested_base_quantity(db, product, data.quantity, data.unit, data.variant_id)
        plan = plan_consumption(
            _available_items(db, user, product.id, data.location_id), requested, date.today()
        )
        if not plan.sufficient:
            raise InsufficientStock(
                "Die Entnahme übersteigt den verfügbaren Bestand. Falls der tatsächliche "
                "Bestand abweicht, bitte eine Bestandskorrektur über die Inventur vornehmen.",
                details={"requested": float(requested), "available": float(plan.available)},
            )
        allocations = [
            AllocationIn(stock_item_id=a.position.id, quantity=a.quantity) for a in plan.allocations
        ]
    return _take(
        db, user, product, allocations,
        MovementType.CONSUMPTION, StockStatus.CONSUMED, None, data.comment,
    )  # fmt: skip


def book_disposal(db: Session, user: User, data: DisposalCreate) -> BookingResult:
    """Entsorgung mit Grund (FR-CNS-008) – reduziert den Bestand, ist aber kein Verbrauch."""
    product = catalog.get_product(db, user.household_id, data.product_id)
    return _take(
        db, user, product, data.allocations,
        MovementType.DISPOSAL, StockStatus.DISPOSED, data.reason.value, data.comment,
    )  # fmt: skip


def book_transfer(db: Session, user: User, data: TransferCreate) -> BookingResult:
    """Umlagerung, auch von Teilmengen (FR-MOV-001/002, BR-005).

    Haltbarkeit, Variante und Öffnungsdatum bleiben erhalten. Existiert am Ziel eine
    Position mit identischen Merkmalen, wird die Menge dort addiert.
    """
    source = db.get(StockItem, data.stock_item_id)
    if source is None or source.household_id != user.household_id:
        raise NotFoundError("Bestandsposition nicht gefunden.", code="stock_item_not_found")
    product = source.product
    target_location = locations.get_active_location(db, user.household_id, data.target_location_id)
    if target_location.id == source.location_id:
        raise ValidationFailed("Ziel- und Ausgangslagerplatz sind identisch.", code="same_location")

    lock_product(db, product.id)
    source = _load_for_update(
        db,
        user,
        product.id,
        AllocationIn(
            stock_item_id=data.stock_item_id,
            quantity=data.quantity,
            expected_version=data.expected_version,
        ),
    )
    qty = normalize(data.quantity)
    source_location_id = source.location_id

    target = db.scalar(
        select(StockItem)
        .where(
            StockItem.household_id == user.household_id,
            StockItem.product_id == product.id,
            StockItem.location_id == target_location.id,
            StockItem.status == StockStatus.AVAILABLE,
            StockItem.expiry_type == source.expiry_type,
            StockItem.variant_id.is_(None) if source.variant_id is None
            else StockItem.variant_id == source.variant_id,
            StockItem.expiry_date.is_(None) if source.expiry_date is None
            else StockItem.expiry_date == source.expiry_date,
            StockItem.opened_on.is_(None) if source.opened_on is None
            else StockItem.opened_on == source.opened_on,
        )
        .with_for_update(of=StockItem)
        .limit(1)
    )  # fmt: skip

    if target is None and qty == source.quantity:
        # Ganze Position verschieben: Identität und Historie der Position bleiben erhalten.
        target = source
        source.location_id = target_location.id
    else:
        source.quantity = normalize(source.quantity - qty)
        if source.quantity == 0:
            source.status = StockStatus.CONSUMED
        if target is None:
            target = StockItem(
                household_id=user.household_id,
                product_id=product.id,
                variant_id=source.variant_id,
                location_id=target_location.id,
                quantity=qty,
                expiry_type=source.expiry_type,
                expiry_date=source.expiry_date,
                received_on=source.received_on,
                opened_on=source.opened_on,
                note=source.note,
            )
            db.add(target)
        else:
            target.quantity = normalize(target.quantity + qty)
    db.flush()

    transaction_id = uuid.uuid4()
    common = {
        "transaction_id": transaction_id,
        "source_location_id": source_location_id,
        "target_location_id": target_location.id,
        "quantity": qty,
        "comment": data.comment,
    }
    _record(
        db, user, source, movement_type=MovementType.TRANSFER_OUT, quantity_delta=-qty, **common
    )
    _record(db, user, target, movement_type=MovementType.TRANSFER_IN, quantity_delta=qty, **common)
    db.flush()

    ctx = item_context(db, user.household_id)
    items = [source] if source is target else [source, target]
    return BookingResult(
        transaction_id=transaction_id,
        product=catalog.product_out(db, product),
        stock_items=[item_out(i, ctx) for i in items],
        quantity=qty,
    )


def reverse_transaction(
    db: Session, user: User, transaction_id: uuid.UUID, data: ReversalCreate
) -> BookingResult:
    """Storno einer Buchung durch nachvollziehbare Gegenbuchung (Spez. 4.6, BR-018).

    Die ursprünglichen Bewegungen bleiben unverändert. Ist der Bestand inzwischen
    weiterverwendet worden (Gegenbuchung würde negativ), wird der Storno abgelehnt.
    """
    movements = list(
        db.scalars(
            select(StockMovement)
            .where(
                StockMovement.household_id == user.household_id,
                StockMovement.transaction_id == transaction_id,
            )
            .order_by(StockMovement.created_at, StockMovement.id)
        )
    )
    if not movements:
        raise NotFoundError("Buchung nicht gefunden.", code="transaction_not_found")
    if any(m.movement_type == MovementType.REVERSAL for m in movements):
        raise ValidationFailed(
            "Ein Storno kann nicht storniert werden. Bitte stattdessen neu buchen.",
            code="reversal_of_reversal",
        )
    if any(
        m.movement_type == MovementType.INVENTORY_CORRECTION for m in movements
    ):  # pragma: no cover – ab Phase 6
        raise ValidationFailed(
            "Inventurkorrekturen werden über eine neue Inventur berichtigt.",
            code="reversal_not_supported",
        )
    ids = [m.id for m in movements]
    if db.scalar(select(exists().where(StockMovement.reverses_movement_id.in_(ids)))):
        raise ConflictError("Diese Buchung wurde bereits storniert.", code="already_reversed")

    product_ids = sorted({m.product_id for m in movements}, key=str)
    for pid in product_ids:
        lock_product(db, pid)

    # Positionen, die als Ganzes verschoben wurden (Ab- und Zugang auf derselben Position),
    # kehren an ihren Ausgangsort zurück.
    out_items = {
        m.stock_item_id: m.source_location_id
        for m in movements
        if m.movement_type == MovementType.TRANSFER_OUT
    }
    whole_moves = {
        m.stock_item_id: out_items[m.stock_item_id]
        for m in movements
        if m.movement_type == MovementType.TRANSFER_IN and m.stock_item_id in out_items
    }

    reversal_id = uuid.uuid4()
    touched: dict[uuid.UUID, StockItem] = {}
    for m in reversed(movements):
        item = touched.get(m.stock_item_id) or db.scalar(
            select(StockItem)
            .where(StockItem.id == m.stock_item_id)
            .with_for_update(of=StockItem)
            .execution_options(populate_existing=True)
        )
        item.quantity = normalize(item.quantity - m.quantity_delta)
        touched[item.id] = item
        _record(
            db,
            user,
            item,
            transaction_id=reversal_id,
            movement_type=MovementType.REVERSAL,
            source_location_id=m.target_location_id,
            target_location_id=m.source_location_id,
            quantity=abs(m.quantity_delta),
            quantity_delta=-m.quantity_delta,
            reverses_movement_id=m.id,
            comment=data.comment,
        )

    for item in touched.values():
        if item.quantity < 0:
            raise ConflictError(
                "Der Storno ist nicht möglich, weil der eingelagerte Bestand inzwischen "
                "bereits entnommen oder umgelagert wurde.",
                code="reversal_not_possible",
            )
        if item.id in whole_moves:
            item.location_id = whole_moves[item.id]
        item.status = StockStatus.AVAILABLE if item.quantity > 0 else StockStatus.CONSUMED
    db.flush()

    product = catalog.get_product(db, user.household_id, movements[0].product_id)
    ctx = item_context(db, user.household_id)
    return BookingResult(
        transaction_id=reversal_id,
        product=catalog.product_out(db, product),
        stock_items=[item_out(i, ctx) for i in touched.values()],
        quantity=sum((abs(m.quantity_delta) for m in movements), Decimal(0)),
    )


def list_movements(
    db: Session,
    household_id: uuid.UUID,
    *,
    product_id=None,
    location_id=None,
    movement_type=None,
    user_id=None,
    transaction_id=None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[MovementOut], int]:
    """Bewegungshistorie, neueste zuerst (Spez. 9.2 „Historie“)."""
    reversal = aliased(StockMovement)
    stmt = (
        select(
            StockMovement,
            Product.name,
            Product.base_unit,
            StockItem.expiry_type,
            StockItem.expiry_date,
            User.display_name,
            exists().where(reversal.reverses_movement_id == StockMovement.id).label("reversed"),
        )
        .join(Product, Product.id == StockMovement.product_id)
        .join(StockItem, StockItem.id == StockMovement.stock_item_id)
        .join(User, User.id == StockMovement.created_by)
        .where(StockMovement.household_id == household_id)
    )
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if location_id:
        ids = locations.subtree_ids(db, household_id, location_id)
        stmt = stmt.where(
            StockMovement.source_location_id.in_(ids) | StockMovement.target_location_id.in_(ids)
        )
    if movement_type:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    if user_id:
        stmt = stmt.where(StockMovement.created_by == user_id)
    if transaction_id:
        stmt = stmt.where(StockMovement.transaction_id == transaction_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(StockMovement.created_at.desc(), StockMovement.id).limit(limit).offset(offset)
    ).all()
    paths = location_paths(db, household_id)
    return [
        MovementOut(
            id=m.id,
            transaction_id=m.transaction_id,
            movement_type=m.movement_type.value,
            product_id=m.product_id,
            product_name=name,
            base_unit=unit,
            stock_item_id=m.stock_item_id,
            expiry_type=etype,
            expiry_date=edate,
            source_location_path=paths.get(m.source_location_id) if m.source_location_id else None,
            target_location_path=paths.get(m.target_location_id) if m.target_location_id else None,
            quantity=m.quantity,
            quantity_delta=m.quantity_delta,
            reason=m.reason,
            comment=m.comment,
            created_at=m.created_at,
            created_by=m.created_by,
            created_by_name=user_name,
            reverses_movement_id=m.reverses_movement_id,
            reversed=rev,
        )
        for m, name, unit, etype, edate, user_name, rev in rows
    ], total


def recent_products(db: Session, user: User, movement_type: MovementType, limit: int = 8):
    """Zuletzt vom Benutzer entnommene Produkte mit Bestand (Schnellentnahme, FR-CNS-007)."""
    last = (
        select(StockMovement.product_id, func.max(StockMovement.created_at).label("last"))
        .where(
            StockMovement.household_id == user.household_id,
            StockMovement.created_by == user.id,
            StockMovement.movement_type == movement_type,
        )
        .group_by(StockMovement.product_id)
        .subquery()
    )
    products = db.scalars(
        select(Product)
        .join(last, last.c.product_id == Product.id)
        .where(Product.active)
        .order_by(last.c.last.desc())
        .limit(limit * 2)
    ).all()
    result = [catalog.product_out(db, p) for p in products]
    return [p for p in result if p.stock_quantity > 0][:limit]


# ------------------------------------------------------------------ Restmenge per Waage


def _grams(value: Decimal) -> str:
    """Deutsche Schreibweise ohne überflüssige Nachkommastellen, z. B. 12.500 → "12,5 g"."""
    text = format(value.normalize(), "f").replace(".", ",")
    return f"{text} g"


def _weighing_for(item: StockItem, measured: Decimal):
    if item.product.base_unit != BaseUnit.GRAM:
        raise ValidationFailed(
            "Restmenge per Waage ist nur bei Produkten in Gramm möglich.",
            code="weigh_requires_gram",
        )
    variant = item.variant
    return compute_weighing(
        item.quantity,
        measured,
        variant.base_quantity if variant else None,
        variant.tare_weight if variant else None,
    )


def _get_item(db: Session, user: User, stock_item_id: uuid.UUID) -> StockItem:
    item = db.get(StockItem, stock_item_id)
    if item is None or item.household_id != user.household_id:
        raise NotFoundError("Bestandsposition nicht gefunden.", code="stock_item_not_found")
    if item.status != StockStatus.AVAILABLE:
        raise InsufficientStock("Die Position ist nicht mehr vorhanden.")
    return item


def weighing_preview(db: Session, user: User, stock_item_id, measured: Decimal) -> WeighingPreview:
    """Berechnet den Verbrauch aus einer Wägung, ohne zu buchen."""
    item = _get_item(db, user, stock_item_id)
    return WeighingPreview(**_weighing_for(item, measured).__dict__)


def book_weighing(db: Session, user: User, data: WeighingCreate) -> BookingResult:
    """Bucht die Differenz zwischen erwartetem und gewogenem Inhalt als Verbrauch (DEC-029).

    Die Berechnung erfolgt unter Produktsperre auf dem aktuellen Stand der Position, nicht
    auf dem Stand, den der Client angezeigt hat."""
    item = _get_item(db, user, data.stock_item_id)
    product = item.product
    lock_product(db, product.id)
    db.refresh(item)
    if data.expected_version is not None and item.version != data.expected_version:
        raise StockChanged(
            "Der Bestand wurde zwischenzeitlich von jemand anderem geändert. "
            "Bitte die Anzeige aktualisieren und erneut wiegen.",
        )
    result = _weighing_for(item, data.measured_weight)
    if result.consumption == 0:
        raise ValidationFailed(
            "Die gewogene Menge entspricht dem bisherigen Bestand – es wurde nichts verbraucht.",
            code="no_consumption",
        )
    note = f"Restmenge gewogen: {_grams(result.net)}"
    if result.tare:
        note += f" (abgelesen {_grams(result.measured)}, Leergewicht {_grams(result.tare)})"
    comment = f"{note}. {data.comment}" if data.comment else note
    return _take(
        db, user, product,
        [AllocationIn(stock_item_id=item.id, quantity=result.consumption)],
        MovementType.CONSUMPTION, StockStatus.CONSUMED, "weighed", comment,
    )  # fmt: skip

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.units import normalize
from app.modules.catalog import service as catalog
from app.modules.catalog.models import Product, ProductVariant
from app.modules.locations import service as locations
from app.modules.locations.models import Location
from app.modules.stock.models import (
    ExpiryType,
    MovementType,
    StockItem,
    StockMovement,
    StockStatus,
)
from app.modules.stock.schemas import (
    LineUnit,
    ReceiptCreate,
    ReceiptDefaults,
    ReceiptResult,
    StockItemOut,
)
from app.modules.users.models import User


def lock_product(db: Session, product_id: uuid.UUID) -> None:
    """Serialisiert alle Bestandsbuchungen eines Produkts bis zum Transaktionsende
    (BR-015, BR-016). Verhindert verlorene Buchungen und Wettläufe beim Zusammenführen."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"product:{product_id}"})


def location_paths(db: Session, household_id: uuid.UUID) -> dict[uuid.UUID, str]:
    return {
        loc.id: loc.path
        for loc in locations.list_locations(db, household_id, include_inactive=True)
    }


def item_out(item: StockItem, paths: dict[uuid.UUID, str]) -> StockItemOut:
    return StockItemOut.model_validate(
        {
            **{k: getattr(item, k) for k in StockItemOut.model_fields if hasattr(item, k)},
            "product_name": item.product.name,
            "product_brand": item.product.brand,
            "base_unit": item.product.base_unit,
            "location_path": paths.get(item.location_id, item.location.name),
        }
    )


def _record(db: Session, user: User, item: StockItem, **kwargs) -> StockMovement:
    movement = StockMovement(
        household_id=user.household_id,
        product_id=item.product_id,
        stock_item_id=item.id,
        created_by=user.id,
        **kwargs,
    )
    db.add(movement)
    return movement


def book_receipt(db: Session, user: User, data: ReceiptCreate) -> ReceiptResult:
    """Einlagerung buchen (FR-STK-001…007). Gleiche bestandsrelevante Merkmale führen zur
    Addition auf die vorhandene Bestandsposition (FR-STK-006, DEC-025)."""
    product = catalog.get_product(db, user.household_id, data.product_id)
    if not product.active:
        raise ValidationFailed("Das Produkt ist deaktiviert.", code="product_inactive")
    variant: ProductVariant | None = None
    if data.variant_id:
        variant = catalog.get_variant(db, product, data.variant_id)
        if not variant.active:
            raise ValidationFailed("Die Variante ist deaktiviert.", code="variant_inactive")
    location = locations.get_active_location(db, user.household_id, data.location_id)

    lock_product(db, product.id)
    transaction_id = uuid.uuid4()
    touched: dict[uuid.UUID, StockItem] = {}
    total = Decimal(0)

    for line in data.lines:
        if line.unit == LineUnit.PACKAGE:
            if variant is None:
                raise ValidationFailed(
                    "Für die Angabe in Packungen muss eine Variante gewählt werden.",
                    code="variant_required",
                )
            qty = normalize(line.quantity * variant.base_quantity)
        else:
            qty = normalize(line.quantity)
        if qty <= 0:
            raise ValidationFailed("Die Menge muss größer als null sein.", code="invalid_quantity")

        item = db.scalar(
            select(StockItem)
            .where(
                StockItem.household_id == user.household_id,
                StockItem.product_id == product.id,
                StockItem.variant_id.is_(None) if variant is None
                else StockItem.variant_id == variant.id,
                StockItem.location_id == location.id,
                StockItem.expiry_type == line.expiry_type,
                StockItem.expiry_date.is_(None) if line.expiry_date is None
                else StockItem.expiry_date == line.expiry_date,
                StockItem.opened_on.is_(None),
                StockItem.status == StockStatus.AVAILABLE,
            )
            .order_by(StockItem.received_on)
            .limit(1)
            .with_for_update(of=StockItem)
        )  # fmt: skip
        if item is None:
            item = StockItem(
                household_id=user.household_id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                location_id=location.id,
                quantity=qty,
                expiry_type=line.expiry_type,
                expiry_date=line.expiry_date,
                received_on=date.today(),
                note=data.note,
            )
            db.add(item)
            db.flush()
        else:
            item.quantity = normalize(item.quantity + qty)
            db.flush()

        _record(
            db,
            user,
            item,
            transaction_id=transaction_id,
            movement_type=MovementType.RECEIPT,
            target_location_id=location.id,
            quantity=qty,
            quantity_delta=qty,
            comment=data.note,
        )
        touched[item.id] = item
        total += qty

    db.flush()
    paths = location_paths(db, user.household_id)
    return ReceiptResult(
        transaction_id=transaction_id,
        product=catalog.product_out(db, product),
        stock_items=[item_out(i, paths) for i in touched.values()],
        received_quantity=total,
    )


def receipt_defaults(db: Session, user: User, product_id: uuid.UUID) -> ReceiptDefaults:
    product = catalog.get_product(db, user.household_id, product_id)
    last = db.execute(
        select(StockItem.variant_id, StockMovement.target_location_id)
        .join(StockItem, StockItem.id == StockMovement.stock_item_id)
        .where(
            StockMovement.product_id == product.id,
            StockMovement.movement_type == MovementType.RECEIPT,
        )
        .order_by(StockMovement.created_at.desc())
        .limit(1)
    ).first()

    active_variants = {v.id: v for v in product.variants if v.active}
    variant_id = last.variant_id if last and last.variant_id in active_variants else None
    if variant_id is None:
        variant_id = next((v.id for v in active_variants.values() if v.is_default), None)

    location_id = product.default_location_id
    if location_id is None and last is not None:
        location_id = last.target_location_id
    if location_id is not None:
        loc = db.get(Location, location_id)
        if loc is None or not loc.active:
            location_id = None

    if product.default_shelf_life_days is not None:
        expiry_type = ExpiryType.BEST_BEFORE
        expiry_date = date.today() + timedelta(days=product.default_shelf_life_days)
    else:
        expiry_type, expiry_date = ExpiryType.BEST_BEFORE, None
    return ReceiptDefaults(
        variant_id=variant_id,
        location_id=location_id,
        expiry_type=expiry_type,
        expiry_date=expiry_date,
    )


def list_stock(
    db: Session,
    household_id: uuid.UUID,
    *,
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    include_sublocations: bool = True,
    category_id: uuid.UUID | None = None,
    q: str | None = None,
    sort: str = "product",
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[StockItemOut], int]:
    """Aktuelle Bestandspositionen (FR-LOC-004, Bestandsübersicht)."""
    stmt = (
        select(StockItem)
        .join(Product, Product.id == StockItem.product_id)
        .where(StockItem.household_id == household_id, StockItem.status == StockStatus.AVAILABLE)
    )
    if product_id:
        stmt = stmt.where(StockItem.product_id == product_id)
    if location_id:
        ids = (
            locations.subtree_ids(db, household_id, location_id)
            if include_sublocations
            else [location_id]
        )
        stmt = stmt.where(StockItem.location_id.in_(ids))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Product.name.ilike(pattern) | Product.brand.ilike(pattern))

    order = {
        "product": (func.lower(Product.name), StockItem.expiry_date.asc().nulls_last()),
        "expiry": (StockItem.expiry_date.asc().nulls_last(), func.lower(Product.name)),
        "received": (StockItem.received_on.desc(), func.lower(Product.name)),
    }.get(sort)
    if order is None:
        raise ValidationFailed("Unbekannte Sortierung.", code="invalid_sort")

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(*order, StockItem.id).limit(limit).offset(offset)).all()
    paths = location_paths(db, household_id)
    return [item_out(i, paths) for i in items], total

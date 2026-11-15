import uuid
from decimal import Decimal

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.barcodes import normalize_barcode
from app.core.errors import ConflictError, NotFoundError, PermissionDenied, ValidationFailed
from app.core.units import BaseUnit, to_base_quantity
from app.modules.catalog.models import (
    DEFAULT_CATEGORIES,
    Product,
    ProductCategory,
    ProductVariant,
)
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    VariantIn,
    VariantOut,
    VariantUpdate,
)
from app.modules.locations.service import get_active_location, subtree_ids
from app.modules.stock.models import StockItem, StockMovement, StockStatus
from app.modules.users.models import User

# ---------------------------------------------------------------- Kategorien


def seed_default_categories(db: Session, household_id: uuid.UUID) -> None:
    """Legt die vorgeschlagenen Produktgruppen an (Spezifikation 4.2), falls keine existieren."""
    if db.scalar(select(exists().where(ProductCategory.household_id == household_id))):
        return
    for i, name in enumerate(DEFAULT_CATEGORIES):
        db.add(ProductCategory(household_id=household_id, name=name, sort_order=i * 10))
    db.flush()


def list_categories(db: Session, household_id: uuid.UUID, include_inactive=False):
    q = select(ProductCategory).where(ProductCategory.household_id == household_id)
    if not include_inactive:
        q = q.where(ProductCategory.active)
    return db.scalars(q.order_by(ProductCategory.sort_order, ProductCategory.name)).all()


def get_category(db: Session, household_id: uuid.UUID, category_id: uuid.UUID):
    cat = db.get(ProductCategory, category_id)
    if cat is None or cat.household_id != household_id:
        raise NotFoundError("Produktgruppe nicht gefunden.", code="category_not_found")
    return cat


def _flush_or_conflict(db: Session, message: str, code: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message, code=code) from exc


def create_category(db: Session, household_id: uuid.UUID, data: CategoryCreate):
    cat = ProductCategory(household_id=household_id, **data.model_dump())
    db.add(cat)
    _flush_or_conflict(db, "Diese Produktgruppe existiert bereits.", "category_name_taken")
    return cat


def update_category(db: Session, household_id, category_id, data: CategoryUpdate):
    cat = get_category(db, household_id, category_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(cat, key, value)
    _flush_or_conflict(db, "Diese Produktgruppe existiert bereits.", "category_name_taken")
    return cat


def delete_category(db: Session, household_id, category_id) -> str:
    cat = get_category(db, household_id, category_id)
    if db.scalar(select(exists().where(Product.category_id == cat.id))):
        cat.active = False
        db.flush()
        return "deactivated"
    db.delete(cat)
    db.flush()
    return "deleted"


# ---------------------------------------------------------------- Produkte


def _stock_totals_subquery():
    return (
        select(StockItem.product_id, func.sum(StockItem.quantity).label("qty"))
        .where(StockItem.status == StockStatus.AVAILABLE)
        .group_by(StockItem.product_id)
        .subquery()
    )


def to_out(product: Product, stock_quantity: Decimal | None = None) -> ProductOut:
    return ProductOut.model_validate(
        {
            **{k: getattr(product, k) for k in ProductOut.model_fields if hasattr(product, k)},
            "category_name": product.category.name,
            "has_image": product.image_path is not None,
            "variants": [VariantOut.model_validate(v) for v in product.variants if v.active],
            "stock_quantity": stock_quantity or Decimal(0),
        }
    )


def product_out(db: Session, product: Product) -> ProductOut:
    qty = db.scalar(
        select(func.coalesce(func.sum(StockItem.quantity), 0)).where(
            StockItem.product_id == product.id, StockItem.status == StockStatus.AVAILABLE
        )
    )
    return to_out(product, qty)


def get_product(db: Session, household_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    p = db.get(Product, product_id)
    if p is None or p.household_id != household_id:
        raise NotFoundError("Produkt nicht gefunden.", code="product_not_found")
    return p


def search_products(
    db: Session,
    household_id: uuid.UUID,
    *,
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    brand: str | None = None,
    barcode: str | None = None,
    location_id: uuid.UUID | None = None,
    in_stock: bool | None = None,
    include_inactive: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ProductOut], int]:
    """Produktsuche nach Name, Kategorie, Hersteller, Barcode und Lagerplatz (FR-PRD-005)."""
    totals = _stock_totals_subquery()
    stmt: Select = (
        select(Product, func.coalesce(totals.c.qty, 0))
        .outerjoin(totals, totals.c.product_id == Product.id)
        .where(Product.household_id == household_id)
    )
    if not include_inactive:
        stmt = stmt.where(Product.active)
    if q:
        pattern = f"%{q.strip()}%"
        barcode_match = exists().where(
            ProductVariant.product_id == Product.id, ProductVariant.barcode.ilike(pattern)
        )
        stmt = stmt.where(
            or_(Product.name.ilike(pattern), Product.brand.ilike(pattern), barcode_match)
        )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand.strip()}%"))
    if barcode:
        code = normalize_barcode(barcode)
        stmt = stmt.where(
            exists().where(ProductVariant.product_id == Product.id, ProductVariant.barcode == code)
        )
    if location_id:
        loc_ids = subtree_ids(db, household_id, location_id)
        stmt = stmt.where(
            exists().where(
                StockItem.product_id == Product.id,
                StockItem.location_id.in_(loc_ids),
                StockItem.status == StockStatus.AVAILABLE,
            )
        )
    if in_stock is True:
        stmt = stmt.where(totals.c.qty > 0)
    elif in_stock is False:
        stmt = stmt.where(func.coalesce(totals.c.qty, 0) == 0)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(func.lower(Product.name), Product.brand).limit(limit).offset(offset)
    ).all()
    return [to_out(p, qty) for p, qty in rows], total


def _product_has_history(db: Session, product_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(
                or_(
                    exists().where(StockItem.product_id == product_id),
                    exists().where(StockMovement.product_id == product_id),
                )
            )
        )
    )


def _validate_refs(db: Session, household_id, category_id=None, default_location_id=None):
    if category_id:
        cat = get_category(db, household_id, category_id)
        if not cat.active:
            raise ValidationFailed("Die Produktgruppe ist nicht aktiv.", code="category_inactive")
    if default_location_id:
        get_active_location(db, household_id, default_location_id)


def _build_variant(product: Product, data: VariantIn) -> ProductVariant:
    return ProductVariant(
        household_id=product.household_id,
        product=product,
        name=data.name,
        barcode=normalize_barcode(data.barcode) if data.barcode else None,
        package_quantity=data.package_quantity,
        package_unit=data.package_unit,
        base_quantity=to_base_quantity(data.package_quantity, data.package_unit, product.base_unit),
        tare_weight=data.tare_weight,
        is_default=data.is_default,
    )


def _ensure_single_default(product: Product, chosen: ProductVariant | None = None) -> None:
    active = [v for v in product.variants if v.active]
    defaults = [v for v in active if v.is_default]
    keep = (
        chosen if chosen is not None and chosen.is_default else (defaults[0] if defaults else None)
    )
    if keep is None and active:
        keep = active[0]
    for v in product.variants:
        v.is_default = v is keep


def _flush_barcode(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if "uq_product_variants_barcode" in str(exc.orig):
            raise ConflictError(
                "Dieser Barcode ist bereits einem anderen Produkt zugeordnet.",
                code="barcode_taken",
            ) from exc
        raise


def _check_barcode_free(db: Session, household_id, code: str | None, own_variant_id=None):
    if not code:
        return
    other = db.scalar(
        select(ProductVariant).where(
            ProductVariant.household_id == household_id,
            ProductVariant.barcode == code,
            ProductVariant.id != own_variant_id if own_variant_id else True,
        )
    )
    if other is not None:
        raise ConflictError(
            f"Der Barcode {code} ist bereits dem Produkt „{other.product.name}“ zugeordnet.",
            code="barcode_taken",
            details={"product_id": str(other.product_id), "variant_id": str(other.id)},
        )


def _check_weigh_remaining(enabled: bool, base_unit: BaseUnit) -> None:
    if enabled and base_unit != BaseUnit.GRAM:
        raise ValidationFailed(
            "Restmenge per Waage ist nur bei Produkten mit der Basiseinheit Gramm möglich.",
            code="weigh_requires_gram",
        )


def create_product(db: Session, user: User, data: ProductCreate) -> Product:
    if not user.is_admin and (data.minimum_stock is not None or data.target_stock is not None):
        raise PermissionDenied(
            "Mindest- und Zielbestände dürfen nur Administratoren festlegen.",
            code="stock_levels_admin_only",
        )
    _validate_refs(db, user.household_id, data.category_id, data.default_location_id)
    _check_weigh_remaining(data.weigh_remaining, data.base_unit)
    product = Product(
        household_id=user.household_id,
        **data.model_dump(exclude={"variants", "external_image_url"}),
    )
    db.add(product)
    seen = set()
    for v in data.variants:
        variant = _build_variant(product, v)
        if variant.barcode in seen:
            raise ValidationFailed(
                "Ein Barcode wurde mehrfach angegeben.", code="barcode_duplicate"
            )
        if variant.barcode:
            seen.add(variant.barcode)
        _check_barcode_free(db, user.household_id, variant.barcode)
        db.add(variant)
    db.flush()
    db.refresh(product)
    _ensure_single_default(product)
    _flush_barcode(db)
    return product


def update_product(db: Session, household_id, product_id, data: ProductUpdate) -> Product:
    product = get_product(db, household_id, product_id)
    changes = data.model_dump(exclude_unset=True)
    _validate_refs(db, household_id, changes.get("category_id"), changes.get("default_location_id"))

    new_unit = changes.get("base_unit")
    if new_unit is not None and new_unit != product.base_unit:
        # FR-PRD-006: Änderungen der Basiseinheit dürfen bestehende Bestände nicht verfälschen.
        if _product_has_history(db, product.id):
            raise ConflictError(
                "Die Basiseinheit kann nicht geändert werden, da für das Produkt bereits "
                "Bestände oder Buchungen existieren.",
                code="base_unit_locked",
            )
        for v in product.variants:
            v.base_quantity = to_base_quantity(
                v.package_quantity, v.package_unit, BaseUnit(new_unit)
            )

    _check_weigh_remaining(
        changes.get("weigh_remaining", product.weigh_remaining) or False,
        BaseUnit(changes.get("base_unit") or product.base_unit),
    )

    minimum = changes.get("minimum_stock", product.minimum_stock)
    target = changes.get("target_stock", product.target_stock)
    if minimum is not None and target is not None and target < minimum:
        raise ValidationFailed(
            "Der Zielbestand darf nicht kleiner als der Mindestbestand sein.",
            code="target_below_minimum",
        )

    nullable = {
        "brand", "minimum_stock", "target_stock", "default_location_id",
        "default_shelf_life_days", "expiry_warning_days", "notes",
    }  # fmt: skip
    for key, value in changes.items():
        if value is None and key not in nullable:
            continue
        setattr(product, key, value)
    db.flush()
    return product


def delete_product(db: Session, household_id, product_id) -> None:
    """Physische Löschung nur ohne Bestands- oder Bewegungshistorie (BR-013)."""
    product = get_product(db, household_id, product_id)
    if _product_has_history(db, product.id):
        raise ConflictError(
            "Das Produkt besitzt Bestände oder eine Buchungshistorie und kann nicht gelöscht "
            "werden. Es kann stattdessen deaktiviert werden.",
            code="product_has_history",
        )
    db.delete(product)
    db.flush()


# ---------------------------------------------------------------- Varianten / Barcodes


def get_variant(db: Session, product: Product, variant_id: uuid.UUID) -> ProductVariant:
    v = db.get(ProductVariant, variant_id)
    if v is None or v.product_id != product.id:
        raise NotFoundError("Variante nicht gefunden.", code="variant_not_found")
    return v


def add_variant(db: Session, household_id, product_id, data: VariantIn) -> ProductVariant:
    product = get_product(db, household_id, product_id)
    variant = _build_variant(product, data)
    _check_barcode_free(db, household_id, variant.barcode)
    db.add(variant)
    db.flush()
    db.refresh(product)
    _ensure_single_default(product, variant)
    _flush_barcode(db)
    return variant


def update_variant(db: Session, household_id, product_id, variant_id, data: VariantUpdate):
    product = get_product(db, household_id, product_id)
    variant = get_variant(db, product, variant_id)
    changes = data.model_dump(exclude_unset=True)
    if "barcode" in changes:
        variant.barcode = normalize_barcode(changes["barcode"]) if changes["barcode"] else None
        _check_barcode_free(db, household_id, variant.barcode, variant.id)
    if "name" in changes:
        variant.name = changes["name"]
    if "tare_weight" in changes:
        variant.tare_weight = changes["tare_weight"]
    if changes.get("package_quantity") is not None:
        variant.package_quantity = changes["package_quantity"]
    if changes.get("package_unit") is not None:
        variant.package_unit = changes["package_unit"]
    # Bestände sind in der Basiseinheit gespeichert und bleiben von dieser Änderung unberührt.
    variant.base_quantity = to_base_quantity(
        variant.package_quantity, variant.package_unit, product.base_unit
    )
    if changes.get("is_default") is not None:
        variant.is_default = changes["is_default"]
        _ensure_single_default(product, variant)
    _flush_barcode(db)
    return variant


def remove_variant(db: Session, household_id, product_id, variant_id) -> str:
    product = get_product(db, household_id, product_id)
    variant = get_variant(db, product, variant_id)
    used = db.scalar(select(exists().where(StockItem.variant_id == variant.id)))
    if used:
        # Historie bleibt erhalten; der Barcode wird für andere Varianten wieder frei.
        variant.active = False
        variant.barcode = None
        variant.is_default = False
        result = "deactivated"
    else:
        db.delete(variant)
        product.variants.remove(variant)
        result = "deleted"
    db.flush()
    _ensure_single_default(product)
    db.flush()
    return result


def lookup_barcode(db: Session, household_id, raw: str) -> tuple[Product, ProductVariant]:
    code = normalize_barcode(raw)
    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.household_id == household_id,
            ProductVariant.barcode == code,
            ProductVariant.active,
        )
    )
    if variant is None:
        raise NotFoundError(
            "Der Barcode ist noch keinem Produkt zugeordnet.",
            code="barcode_unknown",
            details={"barcode": code},
        )
    return variant.product, variant

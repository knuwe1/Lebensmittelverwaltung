import uuid

from sqlalchemy import exists, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.modules.locations.models import Location
from app.modules.locations.schemas import LocationCreate, LocationOut, LocationUpdate
from app.modules.stock.models import StockItem, StockMovement, StockStatus

PATH_SEPARATOR = " › "


def get_location(db: Session, household_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    loc = db.get(Location, location_id)
    if loc is None or loc.household_id != household_id:
        raise NotFoundError("Lagerplatz nicht gefunden.", code="location_not_found")
    return loc


def get_active_location(db: Session, household_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    loc = get_location(db, household_id, location_id)
    if not loc.active:
        raise ValidationFailed("Der Lagerplatz ist nicht mehr aktiv.", code="location_inactive")
    return loc


def subtree_ids(db: Session, household_id: uuid.UUID, root_id: uuid.UUID) -> list[uuid.UUID]:
    """Liefert den Lagerplatz und sämtliche (auch indirekt) untergeordneten Lagerplätze."""
    base = select(Location.id, literal(0).label("depth")).where(
        Location.id == root_id, Location.household_id == household_id
    )
    tree = base.cte("tree", recursive=True)
    tree = tree.union_all(
        select(Location.id, (tree.c.depth + 1).label("depth")).where(
            Location.parent_id == tree.c.id
        )
    )
    return list(db.scalars(select(tree.c.id)))


def _with_paths(locations: list[Location]) -> list[LocationOut]:
    by_id = {loc.id: loc for loc in locations}

    def path(loc: Location) -> str:
        parts, seen, cur = [], set(), loc
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            parts.append(cur.name)
            cur = by_id.get(cur.parent_id) if cur.parent_id else None
        return PATH_SEPARATOR.join(reversed(parts))

    out = [
        LocationOut.model_validate(loc, from_attributes=True).model_copy(update={"path": path(loc)})
        for loc in locations
    ]
    return sorted(out, key=lambda o: o.path.lower())


def list_locations(db: Session, household_id: uuid.UUID, include_inactive=False):
    q = select(Location).where(Location.household_id == household_id)
    if not include_inactive:
        q = q.where(Location.active)
    return _with_paths(list(db.scalars(q)))


def location_out(db: Session, loc: Location) -> LocationOut:
    all_locs = list(db.scalars(select(Location).where(Location.household_id == loc.household_id)))
    return next(o for o in _with_paths(all_locs) if o.id == loc.id)


def _flush_unique(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "Ein Lagerplatz mit diesem Namen existiert an dieser Stelle bereits.",
            code="location_name_taken",
        ) from exc


def create_location(db: Session, household_id: uuid.UUID, data: LocationCreate) -> Location:
    if data.parent_id:
        get_active_location(db, household_id, data.parent_id)
    loc = Location(household_id=household_id, **data.model_dump())
    db.add(loc)
    _flush_unique(db)
    return loc


def update_location(
    db: Session, household_id: uuid.UUID, location_id: uuid.UUID, data: LocationUpdate
) -> Location:
    loc = get_location(db, household_id, location_id)
    changes = data.model_dump(exclude_unset=True)
    if "parent_id" in changes and changes["parent_id"] != loc.parent_id:
        new_parent = changes["parent_id"]
        if new_parent is not None:
            get_active_location(db, household_id, new_parent)
            if new_parent in subtree_ids(db, household_id, loc.id):
                raise ValidationFailed(
                    "Ein Lagerplatz kann nicht unter sich selbst oder einen seiner "
                    "Unterlagerplätze verschoben werden.",
                    code="location_cycle",
                )
    for key, value in changes.items():
        if key == "name" and value is None:
            continue
        setattr(loc, key, value)
    _flush_unique(db)
    return loc


def delete_location(db: Session, household_id: uuid.UUID, location_id: uuid.UUID) -> str:
    """Entfernt einen Lagerplatz (FR-LOC-003, BR-012).

    Mit Bestand: Abbruch mit Liste der blockierenden Bestände.
    Mit Historie: Deaktivierung statt physischer Löschung (Datenhistorie bleibt erhalten).
    Rückgabe: "deleted" oder "deactivated".
    """
    loc = get_location(db, household_id, location_id)

    children = db.scalar(select(exists().where(Location.parent_id == loc.id, Location.active)))
    if children:
        raise ConflictError(
            "Der Lagerplatz enthält noch Unterlagerplätze. Bitte diese zuerst verschieben "
            "oder entfernen.",
            code="location_has_children",
        )

    blocking = db.scalars(
        select(StockItem).where(
            StockItem.location_id == loc.id, StockItem.status == StockStatus.AVAILABLE
        )
    ).all()
    if blocking:
        raise ConflictError(
            "Am Lagerplatz sind noch Bestände vorhanden. Bitte zuerst umlagern, verbrauchen "
            "oder ausbuchen.",
            code="location_has_stock",
            details=[
                {
                    "stock_item_id": str(s.id),
                    "product_id": str(s.product_id),
                    "product_name": s.product.name,
                    "quantity": float(s.quantity),
                    "base_unit": s.product.base_unit.value,
                }
                for s in blocking
            ],
        )

    has_history = db.scalar(
        select(
            or_(
                exists().where(StockItem.location_id == loc.id),
                exists().where(
                    or_(
                        StockMovement.source_location_id == loc.id,
                        StockMovement.target_location_id == loc.id,
                    )
                ),
                # deaktivierte Unterlagerplätze verweisen weiterhin auf diesen Lagerplatz
                exists().where(Location.parent_id == loc.id),
            )
        )
    )
    if has_history:
        loc.active = False
        db.flush()
        return "deactivated"
    db.delete(loc)
    db.flush()
    return "deleted"

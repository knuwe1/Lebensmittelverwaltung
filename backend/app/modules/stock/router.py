import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query

from app.api.deps import CurrentUser, DbSession
from app.core.idempotency import run_idempotent
from app.core.units import PositiveQuantity
from app.modules.catalog.schemas import ProductOut
from app.modules.stock import movements, service
from app.modules.stock.models import MovementType
from app.modules.stock.schemas import (
    BookingResult,
    ConsumptionCreate,
    ConsumptionPlan,
    DisposalCreate,
    LineUnit,
    MovementPage,
    ReceiptCreate,
    ReceiptDefaults,
    ReceiptResult,
    ReversalCreate,
    StockLevelOut,
    StockPage,
    TransferCreate,
    WeighingCreate,
    WeighingPreview,
)
from app.modules.stock.status import ExpiryStatus, StockLevelStatus

router = APIRouter(prefix="/stock", tags=["Bestand"])

IDEMPOTENCY_DOC = (
    "Pflicht-Header `Idempotency-Key`: eindeutige Kennung je Buchungsvorgang. "
    "Eine Wiederholung mit demselben Schlüssel liefert das ursprüngliche Ergebnis, "
    "ohne erneut zu buchen (Antwort-Header `Idempotent-Replayed: true`)."
)


@router.get("", response_model=StockPage)
def list_stock(
    db: DbSession,
    user: CurrentUser,
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    include_sublocations: bool = True,
    category_id: uuid.UUID | None = None,
    q: str | None = None,
    sort: Literal["product", "expiry", "received"] = "product",
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    items, total = service.list_stock(
        db,
        user.household_id,
        product_id=product_id,
        location_id=location_id,
        include_sublocations=include_sublocations,
        category_id=category_id,
        q=q,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return StockPage(items=items, total=total)


@router.get("/expiring", response_model=StockPage)
def expiring_stock(
    db: DbSession,
    user: CurrentUser,
    location_id: uuid.UUID | None = None,
    include_sublocations: bool = True,
    status: Annotated[list[ExpiryStatus] | None, Query()] = None,
    sort: Literal["expiry", "product", "location"] = "expiry",
):
    """Gefährdete Lebensmittel (FR-EXP-004): Haltbarkeitsdatum innerhalb der Warnfrist,
    heute erreicht oder überschritten. Mit `status` lässt sich auf einzelne Stufen
    (`expiring`, `due`, `expired`) einschränken."""
    items = service.expiry_overview(
        db,
        user.household_id,
        location_id=location_id,
        include_sublocations=include_sublocations,
        statuses=status or service.ATTENTION_STATUSES,
        sort=sort,
    )
    return StockPage(items=items, total=len(items))


@router.get("/levels", response_model=list[StockLevelOut])
def stock_levels(
    db: DbSession,
    user: CurrentUser,
    status: Annotated[list[StockLevelStatus] | None, Query()] = None,
):
    """Bestandsstatus aller Produkte mit Mindestbestand, dringendste zuerst
    (FR-SHP-003/004). Ohne `status` werden alle überwachten Produkte geliefert."""
    return service.stock_levels(db, user.household_id, status)


@router.get("/receipt-defaults", response_model=ReceiptDefaults)
def receipt_defaults(product_id: uuid.UUID, db: DbSession, user: CurrentUser):
    """Vorschläge für Variante, Lagerplatz und Haltbarkeit bei der Einlagerung."""
    return service.receipt_defaults(db, user, product_id)


@router.post(
    "/receipts", response_model=ReceiptResult, status_code=201, description=IDEMPOTENCY_DOC
)
def book_receipt(
    data: ReceiptCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Einlagerung buchen."""
    return run_idempotent(
        db, user, idempotency_key, "POST /stock/receipts", data,
        lambda: service.book_receipt(db, user, data),
    )  # fmt: skip


@router.get("/consumption-plan", response_model=ConsumptionPlan)
def consumption_plan(
    db: DbSession,
    user: CurrentUser,
    product_id: uuid.UUID,
    quantity: PositiveQuantity,
    unit: LineUnit = LineUnit.BASE,
    variant_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
):
    """FEFO-Vorschlag für eine Entnahme – bucht nichts. Positionen mit überschrittenem
    Verbrauchsdatum werden nicht vorgeschlagen."""
    return movements.consumption_plan(db, user, product_id, quantity, unit, variant_id, location_id)


@router.post(
    "/consumptions", response_model=BookingResult, status_code=201, description=IDEMPOTENCY_DOC
)
def book_consumption(
    data: ConsumptionCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Verbrauch buchen. Übersteigt die Menge den Bestand → 409 `insufficient_stock`;
    wurde eine Position zwischenzeitlich geändert → 409 `stock_changed`."""
    return run_idempotent(
        db, user, idempotency_key, "POST /stock/consumptions", data,
        lambda: movements.book_consumption(db, user, data),
    )  # fmt: skip


@router.post(
    "/disposals", response_model=BookingResult, status_code=201, description=IDEMPOTENCY_DOC
)
def book_disposal(
    data: DisposalCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Entsorgung buchen (mit Grund)."""
    return run_idempotent(
        db, user, idempotency_key, "POST /stock/disposals", data,
        lambda: movements.book_disposal(db, user, data),
    )  # fmt: skip


@router.post(
    "/transfers", response_model=BookingResult, status_code=201, description=IDEMPOTENCY_DOC
)
def book_transfer(
    data: TransferCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Umlagerung einer Bestandsposition (ganz oder teilweise)."""
    return run_idempotent(
        db, user, idempotency_key, "POST /stock/transfers", data,
        lambda: movements.book_transfer(db, user, data),
    )  # fmt: skip


@router.post(
    "/transactions/{transaction_id}/reversal",
    response_model=BookingResult,
    status_code=201,
    description=IDEMPOTENCY_DOC,
)
def reverse_transaction(
    transaction_id: uuid.UUID,
    data: ReversalCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Storniert einen Buchungsvorgang durch Gegenbuchung."""
    return run_idempotent(
        db, user, idempotency_key, f"POST /stock/transactions/{transaction_id}/reversal", data,
        lambda: movements.reverse_transaction(db, user, transaction_id, data),
    )  # fmt: skip


@router.get("/movements", response_model=MovementPage)
def list_movements(
    db: DbSession,
    user: CurrentUser,
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    movement_type: MovementType | None = None,
    user_id: uuid.UUID | None = None,
    transaction_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Bewegungshistorie, neueste zuerst."""
    items, total = movements.list_movements(
        db,
        user.household_id,
        product_id=product_id,
        location_id=location_id,
        movement_type=movement_type,
        user_id=user_id,
        transaction_id=transaction_id,
        limit=limit,
        offset=offset,
    )
    return MovementPage(items=items, total=total)


@router.get("/recent-products", response_model=list[ProductOut])
def recent_products(
    db: DbSession,
    user: CurrentUser,
    movement_type: MovementType = MovementType.CONSUMPTION,
    limit: int = Query(default=8, ge=1, le=30),
):
    """Zuletzt vom Benutzer gebuchte Produkte mit Bestand (Schnellentnahme)."""
    return movements.recent_products(db, user, movement_type, limit)


@router.get("/weighing-preview", response_model=WeighingPreview)
def weighing_preview(
    db: DbSession, user: CurrentUser, stock_item_id: uuid.UUID, measured_weight: PositiveQuantity
):
    """Berechnet aus dem abgelesenen Gewicht der angebrochenen Packung den Verbrauch."""
    return movements.weighing_preview(db, user, stock_item_id, measured_weight)


@router.post(
    "/weighings", response_model=BookingResult, status_code=201, description=IDEMPOTENCY_DOC
)
def book_weighing(
    data: WeighingCreate,
    db: DbSession,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Restmenge per Waage: bucht die Differenz als Verbrauch (Grund `weighed`)."""
    return run_idempotent(
        db, user, idempotency_key, "POST /stock/weighings", data,
        lambda: movements.book_weighing(db, user, data),
    )  # fmt: skip

import uuid
from typing import Literal

from fastapi import APIRouter, Header, Query

from app.api.deps import CurrentUser, DbSession
from app.core.idempotency import run_idempotent
from app.modules.stock import service
from app.modules.stock.schemas import ReceiptCreate, ReceiptDefaults, ReceiptResult, StockPage

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

import io
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core import images
from app.core.barcodes import normalize_barcode
from app.core.errors import ConflictError, DomainError, NotFoundError
from app.integrations.product_data import (
    ExternalServiceError,
    ProductDataSource,
    get_product_data_source,
)
from app.modules.catalog.models import ProductCategory
from app.modules.settings.service import get_settings_for

router = APIRouter(prefix="/product-data", tags=["Externe Produktdaten"])

Source = Annotated[ProductDataSource, Depends(get_product_data_source)]


class ExternalUnavailable(DomainError):
    status_code = 502
    code = "external_unavailable"


class SuggestionOut(BaseModel):
    source: str
    source_url: str
    license: str
    barcode: str
    name: str | None
    brand: str | None
    base_unit: str
    package_quantity: Decimal | None
    package_unit: str | None
    category_id: uuid.UUID | None
    image_url: str | None


def ensure_enabled(db, household_id) -> None:
    if not get_settings_for(db, household_id).external_product_data:
        raise ConflictError(
            "Externe Produktdaten sind nicht aktiviert (Einstellungen → System).",
            code="external_disabled",
        )


@router.get("/barcode/{code}", response_model=SuggestionOut)
def lookup(code: str, db: DbSession, user: CurrentUser, source: Source):
    """Vorschlag aus einer externen Produktdatenbank (FR-PRD-003). Speichert nichts.

    404 `external_not_found`, wenn die Quelle das Produkt nicht kennt; 502
    `external_unavailable`, wenn der Dienst nicht erreichbar ist; 409 `external_disabled`,
    wenn die Integration in den Einstellungen nicht aktiviert ist."""
    ensure_enabled(db, user.household_id)
    barcode = normalize_barcode(code)
    try:
        s = source.lookup(barcode)
    except ExternalServiceError as exc:
        raise ExternalUnavailable(
            f"{source.name} ist derzeit nicht erreichbar. Das Produkt kann manuell angelegt werden."
        ) from exc
    if s is None:
        raise NotFoundError(f"{source.name} kennt diesen Barcode nicht.", code="external_not_found")
    category_id = None
    if s.category_hint:
        category_id = db.scalar(
            select(ProductCategory.id).where(
                ProductCategory.household_id == user.household_id,
                ProductCategory.name == s.category_hint,
                ProductCategory.active,
            )
        )
    return SuggestionOut(**{**s.__dict__, "category_id": category_id})


@router.get("/image", response_class=Response)
def proxy_image(
    db: DbSession,
    user: CurrentUser,
    source: Source,
    url: str = Query(max_length=1000),
):
    """Vorschaubild eines Vorschlags über die eigene Instanz ausliefern: keine Verbindung vom
    Endgerät zum externen Dienst (NFR-DAT-002), Bild wird neu kodiert (NFR-SEC-006)."""
    ensure_enabled(db, user.household_id)
    try:
        raw = source.fetch_image(url)
    except ExternalServiceError as exc:
        raise ExternalUnavailable("Das Bild ist nicht verfügbar.") from exc
    img = images.load_image(raw)
    img.thumbnail((320, 320))
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=80)
    return Response(
        buf.getvalue(), media_type="image/webp", headers={"Cache-Control": "private, max-age=3600"}
    )

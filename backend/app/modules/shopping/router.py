import uuid

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, DbSession
from app.modules.shopping import service
from app.modules.shopping.schemas import (
    RefreshResult,
    ShoppingItemCreate,
    ShoppingItemOut,
    ShoppingItemUpdate,
    ShoppingListOut,
)

router = APIRouter(prefix="/shopping-list", tags=["Einkaufsliste"])


@router.get("", response_model=ShoppingListOut)
def read_list(db: DbSession, user: CurrentUser):
    """Die gemeinsame Einkaufsliste des Haushalts (DEC-018): offen, gekauft, erledigt."""
    result = service.list_out(db, user.household_id)
    db.commit()  # legt die Liste beim ersten Aufruf an
    return result


@router.post("/refresh", response_model=RefreshResult)
def refresh(db: DbSession, user: CurrentUser):
    """Bedarf ermitteln (FR-SHP-005/010). Kann beliebig oft aufgerufen werden, ohne doppelte
    Positionen zu erzeugen; manuelle und bearbeitete Positionen bleiben erhalten."""
    result = service.refresh(db, user)
    db.commit()
    return result


@router.post("/items", response_model=ShoppingItemOut, status_code=201)
def add_item(data: ShoppingItemCreate, db: DbSession, user: CurrentUser):
    """Manuelle Position: Lebensmittel aus dem Katalog oder freier Text (FR-SHP-007)."""
    result = service.add_item(db, user, data)
    db.commit()
    return result


@router.patch("/items/{item_id}", response_model=ShoppingItemOut)
def update_item(item_id: uuid.UUID, data: ShoppingItemUpdate, db: DbSession, user: CurrentUser):
    """Menge, Kommentar, optionale Position übernehmen (`optional: false`), Status
    `open` / `purchased` / `done`. Der Status ändert nie den Bestand (BR-007)."""
    result = service.update_item(db, user, item_id, data)
    db.commit()
    return result


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: uuid.UUID, db: DbSession, user: CurrentUser):
    service.delete_item(db, user, item_id)
    db.commit()
    return Response(status_code=204)


@router.post("/clear-done", response_model=ShoppingListOut)
def clear_done(db: DbSession, user: CurrentUser):
    """Entfernt alle erledigten Positionen."""
    result = service.clear_done(db, user)
    db.commit()
    return result

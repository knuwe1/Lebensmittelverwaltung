import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, InventoryUser
from app.core.errors import ConflictError
from app.modules.inventory import service
from app.modules.inventory.schemas import (
    CountUpdate,
    InventoryConflict,
    InventoryCreate,
    InventoryItemCreate,
    InventoryOut,
)

router = APIRouter(prefix="/inventories", tags=["Inventur"])


@router.get("", response_model=list[InventoryOut])
def list_inventories(db: DbSession, user: CurrentUser):
    """Inventurprotokoll (FR-INV-007): alle Inventuren, neueste zuerst, ohne Positionen."""
    return service.list_inventories(db, user.household_id)


@router.post("", response_model=InventoryOut, status_code=201)
def start(data: InventoryCreate, db: DbSession, user: InventoryUser):
    """Inventur starten (FR-INV-001). Ohne `location_id`: gesamter Haushalt."""
    inv = service.start(db, user, data)
    db.commit()
    return service.inventory_out(db, inv)


@router.get("/{inventory_id}", response_model=InventoryOut)
def read(inventory_id: uuid.UUID, db: DbSession, user: CurrentUser):
    """Inventurliste mit Soll, Ist, Differenz und Konfliktkennzeichen (FR-INV-002/003/007)."""
    return service.inventory_out(db, service.get_inventory(db, user.household_id, inventory_id))


@router.patch("/{inventory_id}/items/{item_id}", response_model=InventoryOut)
def count(
    inventory_id: uuid.UUID,
    item_id: uuid.UUID,
    data: CountUpdate,
    db: DbSession,
    user: InventoryUser,
):
    """Istbestand einer Position erfassen (zwischenspeichern, FR-INV-006)."""
    inv = service.count(db, user, inventory_id, item_id, data)
    db.commit()
    return service.inventory_out(db, inv)


@router.post("/{inventory_id}/items", response_model=InventoryOut, status_code=201)
def add_item(
    inventory_id: uuid.UUID, data: InventoryItemCreate, db: DbSession, user: InventoryUser
):
    """Nicht erfasstes Lebensmittel ergänzen (FR-INV-005)."""
    inv = service.add_item(db, user, inventory_id, data)
    db.commit()
    return service.inventory_out(db, inv)


@router.delete("/{inventory_id}/items/{item_id}", response_model=InventoryOut)
def remove_item(inventory_id: uuid.UUID, item_id: uuid.UUID, db: DbSession, user: InventoryUser):
    """Ergänztes Lebensmittel wieder entfernen."""
    inv = service.remove_item(db, user, inventory_id, item_id)
    db.commit()
    return service.inventory_out(db, inv)


@router.post("/{inventory_id}/accept-remaining", response_model=InventoryOut)
def accept_remaining(inventory_id: uuid.UUID, db: DbSession, user: InventoryUser):
    """Noch nicht gezählte, unveränderte Positionen mit dem Soll übernehmen."""
    inv = service.accept_remaining(db, user, inventory_id)
    db.commit()
    return service.inventory_out(db, inv)


@router.post("/{inventory_id}/check", response_model=list[InventoryConflict])
def check(inventory_id: uuid.UUID, db: DbSession, user: InventoryUser):
    """Zwischenzeitliche Buchungen prüfen (FR-INV-008); neue Positionen werden ergänzt."""
    conflicts = service.sync(db, service.get_inventory(db, user.household_id, inventory_id))
    db.commit()
    return conflicts


@router.post("/{inventory_id}/complete", response_model=InventoryOut)
def complete(inventory_id: uuid.UUID, db: DbSession, user: InventoryUser):
    """Inventur abschließen und Korrekturen buchen (FR-INV-004). 409 `inventory_conflict`
    mit den betroffenen Positionen, falls seit dem Start gebucht wurde (FR-INV-008)."""
    inv = service.get_inventory(db, user.household_id, inventory_id)
    if inv.status == service.InventoryStatus.OPEN:
        conflicts = service.sync(db, inv)
        db.commit()  # neu gefundene Positionen bleiben in der Liste erhalten
        if conflicts:
            raise ConflictError(
                "Seit dem Start der Inventur wurde gebucht. Bitte die markierten Positionen "
                "erneut prüfen.",
                code="inventory_conflict",
                details=[c.model_dump(mode="json") for c in conflicts],
            )
    inv = service.complete(db, user, inventory_id)
    db.commit()
    return service.inventory_out(db, inv)


@router.post("/{inventory_id}/cancel", response_model=InventoryOut)
def cancel(inventory_id: uuid.UUID, db: DbSession, user: InventoryUser):
    """Inventur abbrechen; es wird nichts gebucht."""
    inv = service.cancel(db, user, inventory_id)
    db.commit()
    return service.inventory_out(db, inv)

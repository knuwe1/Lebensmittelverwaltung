import uuid

from fastapi import APIRouter, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.modules.locations import service
from app.modules.locations.schemas import LocationCreate, LocationOut, LocationUpdate

router = APIRouter(prefix="/locations", tags=["Lagerplätze"])


@router.get("", response_model=list[LocationOut])
def list_locations(db: DbSession, user: CurrentUser, include_inactive: bool = False):
    """Alle Lagerplätze als flache Liste mit `parent_id` und vollständigem Pfad."""
    return service.list_locations(db, user.household_id, include_inactive)


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(data: LocationCreate, db: DbSession, admin: AdminUser):
    loc = service.create_location(db, admin.household_id, data)
    db.commit()
    return service.location_out(db, loc)


@router.patch("/{location_id}", response_model=LocationOut)
def update_location(location_id: uuid.UUID, data: LocationUpdate, db: DbSession, admin: AdminUser):
    """Umbenennen oder innerhalb der Hierarchie verschieben (`parent_id`)."""
    loc = service.update_location(db, admin.household_id, location_id, data)
    db.commit()
    return service.location_out(db, loc)


@router.delete("/{location_id}")
def delete_location(location_id: uuid.UUID, db: DbSession, admin: AdminUser):
    """Entfernt einen Lagerplatz. Mit Historie wird er nur deaktiviert (Ergebnis `result`)."""
    result = service.delete_location(db, admin.household_id, location_id)
    db.commit()
    return {"result": result}

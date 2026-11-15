import uuid
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.modules.settings.models import HouseholdSettings


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_product_data: bool
    expiry_warning_days: int
    stock_warning_factor: float


class SettingsUpdate(BaseModel):
    external_product_data: bool | None = None
    expiry_warning_days: int | None = Field(default=None, ge=0, le=365)
    stock_warning_factor: Decimal | None = Field(default=None, ge=1, le=10, decimal_places=2)


def get_settings_for(db: Session, household_id: uuid.UUID) -> HouseholdSettings:
    settings = db.get(HouseholdSettings, household_id)
    if settings is None:
        db.execute(
            insert(HouseholdSettings)
            .values(household_id=household_id)
            .on_conflict_do_nothing(index_elements=["household_id"])
        )
        db.flush()
        settings = db.get(HouseholdSettings, household_id)
    return settings


router = APIRouter(prefix="/settings", tags=["Einstellungen"])


@router.get("", response_model=SettingsOut)
def read_settings(db: DbSession, user: CurrentUser):
    s = get_settings_for(db, user.household_id)
    db.commit()
    return s


@router.patch("", response_model=SettingsOut)
def update_settings(data: SettingsUpdate, db: DbSession, admin: AdminUser):
    s = get_settings_for(db, admin.household_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(s, key, value)
    db.commit()
    return s

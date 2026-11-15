import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Benutzer"])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, admin: AdminUser):
    return db.scalars(
        select(User).where(User.household_id == admin.household_id).order_by(User.username)
    ).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DbSession, admin: AdminUser):
    user = service.create_user(db, admin.household_id, data)
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, data: UserUpdate, db: DbSession, admin: AdminUser):
    user = service.update_user(db, admin.household_id, user_id, data)
    db.commit()
    return user

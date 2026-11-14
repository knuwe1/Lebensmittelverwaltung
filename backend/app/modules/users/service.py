import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.security import hash_password
from app.modules.users.models import Household, Role, User
from app.modules.users.schemas import UserCreate, UserUpdate

log = logging.getLogger(__name__)


def create_user(db: Session, household_id, data: UserCreate) -> User:
    exists = db.scalar(select(User.id).where(func.lower(User.username) == data.username.lower()))
    if exists:
        raise ConflictError("Der Benutzername ist bereits vergeben.", code="username_taken")
    user = User(
        household_id=household_id,
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        role=data.role,
        can_do_inventory=data.can_do_inventory,
    )
    db.add(user)
    db.flush()
    return user


def _active_admin_count(db: Session, household_id) -> int:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.household_id == household_id, User.role == Role.ADMIN, User.active)
    )


def update_user(db: Session, household_id, user_id, data: UserUpdate) -> User:
    user = db.get(User, user_id)
    if user is None or user.household_id != household_id:
        raise NotFoundError("Benutzer nicht gefunden.")

    demotes = data.role is not None and data.role != Role.ADMIN and user.is_admin
    deactivates = data.active is False and user.active and user.is_admin
    if (demotes or deactivates) and _active_admin_count(db, household_id) <= 1:
        raise ValidationFailed(
            "Es muss mindestens ein aktiver Administrator verbleiben.", code="last_admin"
        )

    changes = data.model_dump(exclude_unset=True)
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
        user.token_version += 1
    if changes.get("active") is False:
        user.token_version += 1
    for key, value in changes.items():
        if value is not None:
            setattr(user, key, value)
    db.flush()
    return user


def bootstrap_admin(db: Session, username: str, password: str, household_name: str) -> bool:
    """Legt Haushalt und ersten Administrator an, falls noch kein Benutzer existiert."""
    if db.scalar(select(func.count()).select_from(User)):
        return False
    household = db.scalar(select(Household).limit(1))
    if household is None:
        household = Household(name=household_name)
        db.add(household)
        db.flush()
    create_user(
        db,
        household.id,
        UserCreate(username=username, display_name=username, password=password, role=Role.ADMIN),
    )
    db.commit()
    log.info("Administrator '%s' wurde angelegt.", username)
    return True

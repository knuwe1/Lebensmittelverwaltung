import math

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.core.config import get_settings
from app.core.errors import AuthenticationError, TooManyAttempts
from app.core.login_throttle import login_throttle
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.schemas import PasswordChange, UserOut

router = APIRouter(prefix="/auth", tags=["Anmeldung"])

# Konstanter Hash, damit unbekannte Benutzernamen gleich lange prüfen wie bekannte.
_DUMMY_HASH = hash_password("timing-equaliser")


class LoginRequest(BaseModel):
    username: str
    password: str


def _set_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.cookie_name,
        token,
        max_age=s.access_token_ttl_minutes * 60,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=UserOut)
def login(data: LoginRequest, response: Response, db: DbSession):
    """Anmeldung. Nach mehreren Fehlversuchen für denselben Benutzernamen → 429
    `too_many_attempts` mit `Retry-After` (Schutz gegen Durchprobieren von Passwörtern)."""
    wait = login_throttle.wait_seconds(data.username)
    if wait > 0:
        seconds = math.ceil(wait)
        raise TooManyAttempts(
            f"Zu viele Fehlversuche. Bitte in {seconds} Sekunden erneut versuchen.",
            details={"retry_after": seconds},
        )
    user = db.scalar(select(User).where(func.lower(User.username) == data.username.lower()))
    valid = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.active:
        login_throttle.failure(data.username)
        raise AuthenticationError("Benutzername oder Passwort ist falsch.", code="invalid_login")
    login_throttle.success(data.username)
    _set_cookie(response, create_access_token(user.id, user.token_version))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession):
    """Abmelden. Macht alle Anmeldungen dieses Benutzers ungültig – auf allen Geräten –,
    damit ein abgegriffenes Token nicht weiter nutzbar ist (DEC-031)."""
    try:
        user = get_current_user(request, db)
    except AuthenticationError:
        user = None  # bereits abgemeldet bzw. Sitzung abgelaufen
    if user is not None:
        user.token_version += 1
        db.commit()
    response.delete_cookie(get_settings().cookie_name, path="/")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, response: Response, user: CurrentUser, db: DbSession):
    if not verify_password(data.current_password, user.password_hash):
        raise AuthenticationError("Das aktuelle Passwort ist falsch.", code="invalid_password")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    db.commit()
    _set_cookie(response, create_access_token(user.id, user.token_version))

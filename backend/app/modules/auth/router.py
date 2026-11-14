from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import AuthenticationError
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
    user = db.scalar(select(User).where(func.lower(User.username) == data.username.lower()))
    valid = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.active:
        raise AuthenticationError("Benutzername oder Passwort ist falsch.", code="invalid_login")
    _set_cookie(response, create_access_token(user.id, user.token_version))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
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

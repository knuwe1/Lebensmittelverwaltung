import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, PermissionDenied
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.users.models import User

DbSession = Annotated[Session, Depends(get_db)]


def _token_from_request(request: Request) -> str | None:
    token = request.cookies.get(get_settings().cookie_name)
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_current_user(request: Request, db: DbSession) -> User:
    token = _token_from_request(request)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise AuthenticationError("Anmeldung erforderlich.")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Ungültige Sitzung.") from exc
    user = db.get(User, user_id)
    if user is None or not user.active or user.token_version != payload.get("ver"):
        raise AuthenticationError("Sitzung abgelaufen. Bitte erneut anmelden.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise PermissionDenied("Diese Aktion ist Administratoren vorbehalten.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_inventory_permission(user: CurrentUser) -> User:
    if not user.may_do_inventory:
        raise PermissionDenied("Inventuren sind für dieses Benutzerkonto nicht freigegeben.")
    return user


InventoryUser = Annotated[User, Depends(require_inventory_permission)]

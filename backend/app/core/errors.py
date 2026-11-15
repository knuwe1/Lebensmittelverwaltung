"""Einheitliches Fehlerformat der API.

Jeder Fehler wird als ``{"error": {"code": ..., "message": ..., "details": ...}}`` geliefert.
``code`` ist maschinenlesbar und stabil, ``message`` ist eine deutsche, für Benutzer
verständliche Meldung.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationFailed(DomainError):
    status_code = 422
    code = "validation_failed"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "not_authenticated"


class PermissionDenied(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


def _body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


_HTTP_MESSAGES = {
    401: ("not_authenticated", "Anmeldung erforderlich."),
    403: ("forbidden", "Keine Berechtigung für diese Aktion."),
    404: ("not_found", "Ressource nicht gefunden."),
    405: ("method_not_allowed", "Methode nicht erlaubt."),
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_body("validation_failed", "Die Eingaben sind ungültig.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code, message = _HTTP_MESSAGES.get(exc.status_code, ("http_error", str(exc.detail)))
        return JSONResponse(
            status_code=exc.status_code, content=_body(code, message), headers=exc.headers
        )

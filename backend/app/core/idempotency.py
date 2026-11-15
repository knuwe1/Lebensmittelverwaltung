"""Schutz vor Doppelbuchungen per Idempotency-Key (DEC-025, BR-017, NFR-REL-002).

Ablauf innerhalb *einer* Datenbanktransaktion:

1. Datensatz (Benutzer, Schlüssel) per ``INSERT … ON CONFLICT DO NOTHING`` reservieren.
   Läuft parallel eine Anfrage mit demselben Schlüssel, wartet PostgreSQL hier, bis
   diese abgeschlossen ist.
2. Konnte reserviert werden → Buchung ausführen, Antwort speichern, gemeinsam committen.
   Scheitert die Buchung, wird alles zurückgerollt; eine Wiederholung bucht erneut.
3. Existiert der Schlüssel bereits → gespeicherte Antwort unverändert zurückgeben.
"""

import hashlib
import json
from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import DomainError, ValidationFailed
from app.modules.stock.models import IdempotencyRecord
from app.modules.users.models import User

HEADER = "Idempotency-Key"


class IdempotencyKeyReused(DomainError):
    status_code = 422
    code = "idempotency_key_reused"


def _hash(endpoint: str, payload: BaseModel) -> str:
    raw = json.dumps(
        {"endpoint": endpoint, "body": payload.model_dump(mode="json")},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def run_idempotent(
    db: Session,
    user: User,
    key: str | None,
    endpoint: str,
    payload: BaseModel,
    action: Callable[[], Any],
    status_code: int = 201,
) -> JSONResponse:
    if not key or not 8 <= len(key) <= 100:
        raise ValidationFailed(
            f"Der Header '{HEADER}' (8–100 Zeichen) ist für Buchungen erforderlich.",
            code="idempotency_key_missing",
        )
    request_hash = _hash(endpoint, payload)
    reserved = db.execute(
        insert(IdempotencyRecord)
        .values(user_id=user.id, key=key, endpoint=endpoint, request_hash=request_hash)
        .on_conflict_do_nothing()
        .returning(IdempotencyRecord.key)
    ).scalar()

    if reserved is None:
        record = db.get(IdempotencyRecord, (user.id, key), populate_existing=True)
        db.rollback()
        if record is None or record.status_code is None:  # pragma: no cover – Wettlauf
            raise ValidationFailed("Die Anfrage wird noch verarbeitet.", code="in_progress")
        if record.request_hash != request_hash:
            raise IdempotencyKeyReused(
                "Die vorherige Buchung wurde bereits gespeichert. Bitte den Bestand prüfen und "
                "die geänderte Buchung erneut absenden."
            )
        return JSONResponse(
            record.response_body,
            status_code=record.status_code,
            headers={"Idempotent-Replayed": "true"},
        )

    body = jsonable_encoder(action())
    db.query(IdempotencyRecord).filter_by(user_id=user.id, key=key).update(
        {"status_code": status_code, "response_body": body}
    )
    db.commit()
    return JSONResponse(body, status_code=status_code)

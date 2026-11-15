"""Testinfrastruktur.

Die Tests laufen gegen eine echte PostgreSQL-Datenbank (Transaktionen, Sperren und
Nebenläufigkeit lassen sich nur dort realistisch prüfen). Die Datenbank-URL kommt aus
``LMV_TEST_DATABASE_URL``. Das Schema wird über die Alembic-Migrationen aufgebaut,
womit die Migrationen gleich mitgetestet werden.
"""

import os

os.environ.setdefault(
    "LMV_TEST_DATABASE_URL", "postgresql+psycopg://lmv:lmv@localhost:55433/lmv_test"
)
os.environ["LMV_DATABASE_URL"] = os.environ["LMV_TEST_DATABASE_URL"]
os.environ["LMV_COOKIE_SECURE"] = "false"
os.environ["LMV_SECRET_KEY"] = "test-secret-key-0123456789-abcdefghijkl"
os.environ["LMV_MEDIA_DIR"] = os.environ.get("LMV_TEST_MEDIA_DIR", "/tmp/lmv-test-media")
os.environ.pop("LMV_BOOTSTRAP_ADMIN_USERNAME", None)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.main import create_app
from app.modules.users.models import Household, Role
from app.modules.users.schemas import UserCreate
from app.modules.users.service import create_user

PASSWORD = "geheim-123"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    from app.core.login_throttle import login_throttle

    login_throttle._states.clear()  # Fehlversuche nicht in andere Tests mitnehmen
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def household(db):
    from app.modules.catalog.service import seed_default_categories

    h = Household(name="Testhaushalt")
    db.add(h)
    db.flush()
    seed_default_categories(db, h.id)
    db.commit()
    return h


def _make_user(db, household, username, role):
    user = create_user(
        db,
        household.id,
        UserCreate(username=username, display_name=username.title(), password=PASSWORD, role=role),
    )
    db.commit()
    return user


@pytest.fixture
def admin(db, household):
    return _make_user(db, household, "admin", Role.ADMIN)


@pytest.fixture
def member(db, household):
    return _make_user(db, household, "mitglied", Role.MEMBER)


@pytest.fixture
def app():
    return create_app()


def _login(app, username) -> TestClient:
    client = TestClient(app)
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def anon(app):
    return TestClient(app)


@pytest.fixture
def admin_client(app, admin):
    return _login(app, "admin")


@pytest.fixture
def member_client(app, member):
    return _login(app, "mitglied")


# ------------------------------------------------------------------ Hilfsfunktionen


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def category_id(client, name="Milchprodukte") -> str:
    cats = ok(client.get("/api/v1/categories"))
    return next(c["id"] for c in cats if c["name"] == name)


def make_location(client, name, parent_id=None) -> dict:
    return ok(client.post("/api/v1/locations", json={"name": name, "parent_id": parent_id}), 201)


def make_product(client, name="Milch 3,5 %", base_unit="ml", variants=None, **extra) -> dict:
    payload = {
        "name": name,
        "category_id": category_id(client),
        "base_unit": base_unit,
        "variants": variants or [],
        **extra,
    }
    return ok(client.post("/api/v1/products", json=payload), 201)


def receive(client, product, location, lines, variant_id=None, key=None, status=201):
    import uuid as _uuid

    r = client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": product["id"],
            "variant_id": variant_id,
            "location_id": location["id"],
            "lines": lines,
        },
        headers={"Idempotency-Key": key or str(_uuid.uuid4())},
    )
    return ok(r, status)

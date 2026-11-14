import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import SessionLocal
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import categories as categories_router
from app.modules.catalog.router import products as products_router
from app.modules.locations.router import router as locations_router
from app.modules.stock.router import router as stock_router
from app.modules.users import service as user_service
from app.modules.users.router import router as users_router

API_PREFIX = "/api/v1"


def _configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    _configure_logging()
    s = get_settings()
    if s.bootstrap_admin_username and s.bootstrap_admin_password:
        with SessionLocal() as db:
            user_service.bootstrap_admin(
                db,
                s.bootstrap_admin_username,
                s.bootstrap_admin_password,
                s.bootstrap_household_name,
            )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lebensmittelverwaltung API",
        version="0.1.0",
        description="REST-API der selbst gehosteten Lebensmittel- und Vorratsverwaltung.",
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["System"])
    def health():
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    api.include_router(auth_router)
    api.include_router(users_router)
    api.include_router(categories_router)
    api.include_router(products_router)
    api.include_router(locations_router)
    api.include_router(stock_router)
    app.include_router(api)
    return app


app = create_app()

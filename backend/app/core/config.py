from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Anwendungskonfiguration. Wird ausschließlich aus Umgebungsvariablen gelesen (NFR-SEC-005)."""

    model_config = SettingsConfigDict(env_prefix="LMV_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lmv:lmv@localhost:5432/lmv"
    secret_key: str = Field(default="dev-insecure-change-me-0123456789abcdef", min_length=32)
    access_token_ttl_minutes: int = 60 * 24 * 14
    cookie_name: str = "lmv_session"
    cookie_secure: bool = True

    # Erstanlage eines Administrators beim Start, falls noch kein Benutzer existiert.
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_household_name: str = "Mein Haushalt"

    # Ablage für Produktbilder und temporäre Erkennungsbilder.
    media_dir: str = "/data/media"
    max_upload_bytes: int = 8 * 1024 * 1024

    # Externe Produktdaten (aktiviert wird pro Haushalt in den Einstellungen)
    off_base_url: str = "https://world.openfoodfacts.org"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

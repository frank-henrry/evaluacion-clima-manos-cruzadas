"""Configuracion de la aplicacion, leida desde variables de entorno / .env.

Nada de secrets hardcodeados: `JWT_SECRET` es obligatorio y no tiene default,
si falta la app no arranca.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS = "http://localhost:8080,http://localhost:5173"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Conexion a Postgres (SQLAlchemy async URL, ej: postgresql+asyncpg://user:pass@host:5432/db)
    database_url: str = "postgresql+asyncpg://practica:practica@localhost:5432/practica"

    # JWT: sin default -> obligatorio via entorno.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Origenes permitidos para CORS, separados por coma.
    cors_origins: str = _DEFAULT_CORS

    # Proveedor meteorologico. La key vacia se traduce en 503 al consultar, de
    # modo que health y autenticacion sigan disponibles si falta configurarla.
    weather_api_key: SecretStr = SecretStr("")
    weather_api_base_url: str = "https://api.weatherapi.com/v1"
    weather_api_timeout_seconds: float = Field(default=5.0, gt=0)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

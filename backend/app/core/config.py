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

    # Prediccion (SPEC 04): dias de pronostico real que se consultan; fuera de
    # ese rango se usa el clima tipico del mes segun los historicos.
    weather_forecast_max_days: int = Field(default=3, ge=1)
    # Ubicacion fija del pronostico (Las Manos Cruzadas); nunca viene del usuario.
    prediccion_ubicacion: str = "Huanuco, Peru"
    # Codigo del lugar turistico en `lugar_turistico` (se busca por codigo, no por id).
    prediccion_lugar_codigo: str = "manos-cruzadas"

    # RAG de historicos (SPEC 05): minimo de dias similares para aceptar un
    # nivel de coincidencia y maximo de filas recuperadas por consulta.
    rag_min_resultados: int = Field(default=5, ge=1)
    rag_max_resultados: int = Field(default=10, ge=1)

    # Agente Analista (SPEC 06). La key vacia se traduce en
    # `AnalistaNoDisponibleError` sin llamar a OpenAI. El modelo se toma de
    # `OPENAI_MODEL`; el default solo aplica si la variable no esta definida.
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = Field(default=20.0, gt=0)
    openai_temperature: float = Field(default=0.2, ge=0, le=2)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

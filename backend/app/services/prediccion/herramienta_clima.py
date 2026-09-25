"""Tool Climatica (SPEC 04): clima esperado en Huanuco para una fecha.

- Dentro del rango de pronostico (`0 <= (fecha - hoy).days < WEATHER_FORECAST_MAX_DAYS`)
  usa el pronostico real de WeatherAPI (`fuente="pronostico"`).
- Fuera de rango, o si el proveedor falla por cualquier motivo, usa el clima
  tipico del mes segun `visitas_historicas` (`fuente="estimado_historico"`).
- Sin historicos para ese mes lanza `ContextoNoDisponibleError`.

No conoce HTTP ni FastAPI y nunca registra la API key.
"""

import logging
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ContextoNoDisponibleError,
    WeatherError,
    WeatherProviderResponseError,
)
from app.db.visitas import clima_tipico_del_mes
from app.integrations.weather_api import WeatherApiClient
from app.models.prediccion import CondicionClima, ContextoClima

logger = logging.getLogger(__name__)

_CONDICION_POR_CODIGO: dict[int, CondicionClima] = {
    1000: "Soleado",
    1003: "Parcialmente nublado",
    **dict.fromkeys((1006, 1009, 1030, 1135, 1147), "Nublado"),
    **dict.fromkeys((1063, 1150, 1153, 1180, 1183, 1240), "Lluvia ligera"),
    **dict.fromkeys(
        (1186, 1189, 1192, 1195, 1243, 1246, 1273, 1276), "Lluvia fuerte"
    ),
}
_CONDICION_POR_DEFECTO: CondicionClima = "Nublado"


def _zona_lima() -> tzinfo:
    try:
        return ZoneInfo("America/Lima")
    except ZoneInfoNotFoundError:
        # Sin base tz (p. ej. Windows sin `tzdata`): Peru es UTC-5 fijo, sin horario de verano.
        return timezone(timedelta(hours=-5), "America/Lima")


def hoy_en_lima() -> date:
    """Fecha actual en America/Lima."""
    return datetime.now(_zona_lima()).date()


def mapear_condicion(codigo: int) -> CondicionClima:
    """Traduce `day.condition.code` de WeatherAPI a las 5 categorias del SPEC 03."""
    return _CONDICION_POR_CODIGO.get(codigo, _CONDICION_POR_DEFECTO)


async def obtener_clima(
    fecha: date,
    session: AsyncSession,
    client: WeatherApiClient,
    *,
    lugar_id: int,
    hoy: date | None = None,
    settings: Settings | None = None,
) -> ContextoClima:
    """Clima esperado para `fecha` en `PREDICCION_UBICACION`.

    Firma del SPEC 04 `obtener_clima(fecha, session, client)` ampliada con
    parametros keyword-only:
    - `lugar_id`: id del lugar (`PREDICCION_LUGAR_CODIGO`) para filtrar los
      historicos; lo resuelve el llamador por codigo, nunca con un id fijo.
    - `hoy`: inyectable para tests; por defecto la fecha actual en America/Lima.
    - `settings`: inyectable para tests; por defecto `get_settings()`.

    Raises:
        ContextoNoDisponibleError: si hay que usar el respaldo historico y no
            existen visitas para ese mes.
    """
    cfg = settings or get_settings()
    referencia = hoy if hoy is not None else hoy_en_lima()
    dias_adelante = (fecha - referencia).days

    if 0 <= dias_adelante < cfg.weather_forecast_max_days:
        try:
            return await _desde_pronostico(
                fecha, client, cfg.prediccion_ubicacion, dias_adelante + 1
            )
        except WeatherError as exc:
            # El error del proveedor no se propaga: se degrada al historico.
            logger.warning(
                "Pronostico no disponible para %s (%s); se usa el clima tipico del mes.",
                fecha.isoformat(),
                type(exc).__name__,
            )

    return await _desde_historico(fecha, session, lugar_id)


async def _desde_pronostico(
    fecha: date, client: WeatherApiClient, ubicacion: str, dias: int
) -> ContextoClima:
    respuesta = await client.fetch_forecast(ubicacion, dias)
    dia = next(
        (d for d in respuesta.forecast.forecastday if d.date == fecha),
        None,
    )
    if dia is None:
        raise WeatherProviderResponseError

    return ContextoClima(
        fecha=fecha,
        condicion_clima=mapear_condicion(dia.day.condition.code),
        temperatura_max=dia.day.maxtemp_c,
        fuente="pronostico",
    )


async def _desde_historico(
    fecha: date, session: AsyncSession, lugar_id: int
) -> ContextoClima:
    tipico = await clima_tipico_del_mes(session, lugar_id, fecha.month)
    if tipico is None:
        raise ContextoNoDisponibleError(
            f"No hay visitas historicas para el mes {fecha.month}."
        )

    condicion, temperatura = tipico
    return ContextoClima(
        fecha=fecha,
        condicion_clima=condicion,  # type: ignore[arg-type]  # validado por Pydantic
        temperatura_max=temperatura,
        fuente="estimado_historico",
    )

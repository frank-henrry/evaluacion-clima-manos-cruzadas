"""Pruebas SPEC 04: Tool Climatica, Tool Calendario y clima_tipico_del_mes.

Sin Postgres ni WeatherAPI reales: el proveedor se mockea con
`httpx.MockTransport` y la BD con monkeypatch / una sesion falsa.
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.exceptions import (
    ContextoNoDisponibleError,
    LocationNotFoundError,
    WeatherProviderResponseError,
    WeatherProviderUnavailableError,
)
from app.db import visitas
from app.integrations.weather_api import WeatherApiClient
from app.services.prediccion import herramienta_clima
from app.services.prediccion.herramienta_calendario import obtener_calendario
from app.services.prediccion.herramienta_clima import (
    hoy_en_lima,
    mapear_condicion,
    obtener_clima,
)

HOY = date(2026, 9, 25)
LUGAR_ID = 7


def make_settings(**overrides) -> Settings:
    base = {
        "jwt_secret": "test-secret",
        "weather_api_key": "provider-test-key",
        "weather_api_base_url": "https://weather.test/v1",
        "weather_api_timeout_seconds": 1,
        "weather_forecast_max_days": 3,
        "prediccion_ubicacion": "Huanuco, Peru",
    }
    base.update(overrides)
    return Settings(**base)


def make_client(handler, **overrides) -> WeatherApiClient:
    return WeatherApiClient(
        make_settings(**overrides), transport=httpx.MockTransport(handler)
    )


def forecast_payload(*dias: tuple[date, int, float]) -> dict:
    return {
        "location": {"name": "Huanuco"},
        "forecast": {
            "forecastday": [
                {
                    "date": d.isoformat(),
                    "day": {
                        "maxtemp_c": temp,
                        "condition": {"code": code, "text": "x"},
                    },
                }
                for d, code, temp in dias
            ]
        },
    }


class HistoricoFalso:
    """Reemplazo de clima_tipico_del_mes que registra las llamadas."""

    def __init__(self, resultado=("Nublado", 18.4)) -> None:
        self.resultado = resultado
        self.llamadas: list[tuple] = []

    async def __call__(self, session, lugar_id, mes):
        self.llamadas.append((session, lugar_id, mes))
        return self.resultado


@pytest.fixture
def historico(monkeypatch) -> HistoricoFalso:
    falso = HistoricoFalso()
    monkeypatch.setattr(herramienta_clima, "clima_tipico_del_mes", falso)
    return falso


SESSION = object()


# --- obtener_clima: pronostico ------------------------------------------------


@pytest.mark.asyncio
async def test_manana_usa_pronostico_con_days_2_y_elige_forecastday_correcto(
    historico,
) -> None:
    manana = HOY + timedelta(days=1)
    peticiones: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        peticiones.append(request)
        return httpx.Response(
            200,
            json=forecast_payload((HOY, 1000, 25.0), (manana, 1195, 19.5)),
        )

    settings = make_settings()
    resultado = await obtener_clima(
        manana,
        SESSION,
        make_client(handler),
        lugar_id=LUGAR_ID,
        hoy=HOY,
        settings=settings,
    )

    assert len(peticiones) == 1
    assert peticiones[0].url.path == "/v1/forecast.json"
    assert peticiones[0].url.params["days"] == "2"
    assert peticiones[0].url.params["q"] == "Huanuco, Peru"
    assert resultado.fuente == "pronostico"
    assert resultado.fecha == manana
    assert resultado.condicion_clima == "Lluvia fuerte"
    assert resultado.temperatura_max == 19.5
    assert historico.llamadas == []


@pytest.mark.asyncio
async def test_hoy_usa_pronostico_con_days_1(historico) -> None:
    peticiones: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        peticiones.append(request)
        return httpx.Response(200, json=forecast_payload((HOY, 1003, 22.0)))

    resultado = await obtener_clima(
        HOY, SESSION, make_client(handler), lugar_id=LUGAR_ID, hoy=HOY,
        settings=make_settings(),
    )

    assert peticiones[0].url.params["days"] == "1"
    assert resultado.fuente == "pronostico"
    assert resultado.condicion_clima == "Parcialmente nublado"


@pytest.mark.asyncio
async def test_limite_del_rango_max_days_usa_historico(historico) -> None:
    """dias_adelante == max_days queda fuera del rango (0 <= d < max)."""

    def handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no debe llamarse al proveedor")

    resultado = await obtener_clima(
        HOY + timedelta(days=3), SESSION, make_client(handler), lugar_id=LUGAR_ID,
        hoy=HOY, settings=make_settings(weather_forecast_max_days=3),
    )
    assert resultado.fuente == "estimado_historico"


# --- obtener_clima: respaldo historico ----------------------------------------


@pytest.mark.asyncio
async def test_fecha_6_meses_adelante_usa_historico_sin_llamar_proveedor(
    historico,
) -> None:
    llamadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(500)

    fecha = date(2027, 3, 25)
    resultado = await obtener_clima(
        fecha, SESSION, make_client(handler), lugar_id=LUGAR_ID, hoy=HOY,
        settings=make_settings(),
    )

    assert llamadas == []
    assert resultado.fuente == "estimado_historico"
    assert resultado.fecha == fecha
    assert resultado.condicion_clima == "Nublado"
    assert resultado.temperatura_max == 18.4
    assert historico.llamadas == [(SESSION, LUGAR_ID, 3)]


@pytest.mark.asyncio
async def test_fecha_pasada_usa_historico(historico) -> None:
    llamadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(500)

    resultado = await obtener_clima(
        HOY - timedelta(days=1), SESSION, make_client(handler), lugar_id=LUGAR_ID,
        hoy=HOY, settings=make_settings(),
    )

    assert llamadas == []
    assert resultado.fuente == "estimado_historico"
    assert historico.llamadas == [(SESSION, LUGAR_ID, 9)]


def _handler_503(_: httpx.Request) -> httpx.Response:
    return httpx.Response(503, json={"error": {"code": 9999, "message": "down"}})


def _handler_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("fallo simulado", request=request)


def _handler_sin_forecastday(_: httpx.Request) -> httpx.Response:
    # Solo trae hoy; falta el dia pedido (manana).
    return httpx.Response(200, json=forecast_payload((HOY, 1000, 25.0)))


def _handler_1006(_: httpx.Request) -> httpx.Response:
    return httpx.Response(400, json={"error": {"code": 1006, "message": "x"}})


def _handler_payload_invalido(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"forecast": {"forecastday": [{"date": "x"}]}})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler",
    [
        _handler_503,
        _handler_connect_error,
        _handler_sin_forecastday,
        _handler_1006,
        _handler_payload_invalido,
    ],
    ids=["503", "connect-error", "forecastday-faltante", "1006", "payload-invalido"],
)
async def test_fallo_del_proveedor_degrada_a_historico(historico, handler) -> None:
    manana = HOY + timedelta(days=1)
    resultado = await obtener_clima(
        manana, SESSION, make_client(handler), lugar_id=LUGAR_ID, hoy=HOY,
        settings=make_settings(),
    )

    assert resultado.fuente == "estimado_historico"
    assert resultado.fecha == manana
    assert historico.llamadas == [(SESSION, LUGAR_ID, 9)]


@pytest.mark.asyncio
async def test_key_vacia_degrada_a_historico_sin_peticion(historico) -> None:
    llamadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(200)

    settings = make_settings(weather_api_key="")
    client = WeatherApiClient(settings, transport=httpx.MockTransport(handler))
    resultado = await obtener_clima(
        HOY + timedelta(days=1), SESSION, client, lugar_id=LUGAR_ID, hoy=HOY,
        settings=settings,
    )

    assert llamadas == []
    assert resultado.fuente == "estimado_historico"


@pytest.mark.asyncio
async def test_sin_historicos_lanza_contexto_no_disponible(monkeypatch) -> None:
    monkeypatch.setattr(
        herramienta_clima, "clima_tipico_del_mes", HistoricoFalso(resultado=None)
    )

    def handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no debe llamarse al proveedor")

    with pytest.raises(ContextoNoDisponibleError):
        await obtener_clima(
            date(2027, 3, 25), SESSION, make_client(handler), lugar_id=LUGAR_ID,
            hoy=HOY, settings=make_settings(),
        )


@pytest.mark.asyncio
async def test_proveedor_caido_y_sin_historicos_lanza_contexto_no_disponible(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        herramienta_clima, "clima_tipico_del_mes", HistoricoFalso(resultado=None)
    )
    with pytest.raises(ContextoNoDisponibleError):
        await obtener_clima(
            HOY + timedelta(days=1), SESSION, make_client(_handler_503),
            lugar_id=LUGAR_ID, hoy=HOY, settings=make_settings(),
        )


@pytest.mark.asyncio
async def test_historico_con_condicion_invalida_falla_validacion(monkeypatch) -> None:
    """Defensa: una condicion fuera de las 5 categorias no se acepta en silencio."""
    monkeypatch.setattr(
        herramienta_clima, "clima_tipico_del_mes", HistoricoFalso(("Granizo", 10.0))
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        await obtener_clima(
            date(2027, 3, 25), SESSION, make_client(_handler_503),
            lugar_id=LUGAR_ID, hoy=HOY, settings=make_settings(),
        )


@pytest.mark.asyncio
async def test_hoy_y_settings_por_defecto(monkeypatch, historico) -> None:
    """Sin `hoy` usa hoy_en_lima(); sin `settings` usa get_settings()."""
    monkeypatch.setattr(herramienta_clima, "hoy_en_lima", lambda: HOY)
    monkeypatch.setattr(herramienta_clima, "get_settings", lambda: make_settings())

    def handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no debe llamarse al proveedor")

    resultado = await obtener_clima(
        date(2027, 3, 1), SESSION, make_client(handler), lugar_id=LUGAR_ID
    )
    assert resultado.fuente == "estimado_historico"


# --- mapear_condicion / hoy_en_lima -------------------------------------------


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        (1000, "Soleado"),
        (1003, "Parcialmente nublado"),
        (1006, "Nublado"),
        (1183, "Lluvia ligera"),
        (1195, "Lluvia fuerte"),
        (9999, "Nublado"),
    ],
)
def test_mapear_condicion(codigo: int, esperado: str) -> None:
    assert mapear_condicion(codigo) == esperado


def test_hoy_en_lima_devuelve_date() -> None:
    hoy = hoy_en_lima()
    assert isinstance(hoy, date)
    assert abs((hoy - date.today()).days) <= 1


def test_zona_lima_sin_tzdata_usa_utc_menos_5(monkeypatch) -> None:
    from zoneinfo import ZoneInfoNotFoundError

    def sin_tz(_: str):
        raise ZoneInfoNotFoundError("sin tzdata")

    monkeypatch.setattr(herramienta_clima, "ZoneInfo", sin_tz)
    zona = herramienta_clima._zona_lima()
    assert zona.utcoffset(None) == timedelta(hours=-5)
    assert isinstance(hoy_en_lima(), date)


# --- WeatherApiClient.fetch_forecast ------------------------------------------


@pytest.mark.asyncio
async def test_fetch_forecast_envia_params_y_parsea() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/forecast.json"
        assert request.url.params["key"] == "provider-test-key"
        assert request.url.params["q"] == "Huanuco, Peru"
        assert request.url.params["days"] == "3"
        assert request.url.params["lang"] == "es"
        return httpx.Response(200, json=forecast_payload((HOY, 1183, 21.3)))

    resultado = await make_client(handler).fetch_forecast("Huanuco, Peru", 3)

    dia = resultado.forecast.forecastday[0]
    assert dia.date == HOY
    assert dia.day.maxtemp_c == 21.3
    assert dia.day.condition.code == 1183


@pytest.mark.asyncio
async def test_fetch_forecast_1006_lanza_location_not_found() -> None:
    with pytest.raises(LocationNotFoundError):
        await make_client(_handler_1006).fetch_forecast("NoExiste", 1)


@pytest.mark.asyncio
async def test_fetch_forecast_503_lanza_unavailable() -> None:
    with pytest.raises(WeatherProviderUnavailableError):
        await make_client(_handler_503).fetch_forecast("Huanuco", 1)


@pytest.mark.asyncio
async def test_fetch_forecast_error_sin_json_lanza_unavailable() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>bad gateway</html>")

    with pytest.raises(WeatherProviderUnavailableError):
        await make_client(handler).fetch_forecast("Huanuco", 1)


@pytest.mark.asyncio
async def test_fetch_forecast_connect_error_lanza_unavailable() -> None:
    with pytest.raises(WeatherProviderUnavailableError):
        await make_client(_handler_connect_error).fetch_forecast("Huanuco", 1)


@pytest.mark.asyncio
async def test_fetch_forecast_key_vacia_no_realiza_peticion() -> None:
    llamadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(200)

    with pytest.raises(WeatherProviderUnavailableError):
        await make_client(handler, weather_api_key="").fetch_forecast("Huanuco", 1)
    assert llamadas == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(200, json={"location": {"name": "Huanuco"}}),
        httpx.Response(200, json={"forecast": {"forecastday": [{"date": "x"}]}}),
        httpx.Response(200, text="no es json"),
    ],
    ids=["sin-forecast", "forecastday-incompleto", "no-json"],
)
async def test_fetch_forecast_payload_invalido_lanza_response_error(respuesta) -> None:
    with pytest.raises(WeatherProviderResponseError):
        await make_client(lambda _: respuesta).fetch_forecast("Huanuco", 1)


@pytest.mark.asyncio
async def test_fetch_forecast_error_no_expone_key_ni_mensaje() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503, json={"error": {"code": 9999, "message": "secreto-del-proveedor"}}
        )

    with pytest.raises(WeatherProviderUnavailableError) as info:
        await make_client(handler).fetch_forecast("Huanuco", 1)
    assert "provider-test-key" not in str(info.value)
    assert "secreto-del-proveedor" not in str(info.value)


# --- obtener_calendario -------------------------------------------------------


def test_calendario_san_juan_es_fiesta_local() -> None:
    ctx = obtener_calendario(date(2026, 6, 24))
    assert ctx.es_feriado is True
    assert ctx.nombre_feriado == "Fiesta de San Juan"
    assert ctx.dia_semana == "Miércoles"
    assert ctx.fecha == date(2026, 6, 24)


def test_calendario_10_febrero_es_vacacional() -> None:
    ctx = obtener_calendario(date(2026, 2, 10))
    assert ctx.temporada == "vacacional"
    assert ctx.es_feriado is False


def test_calendario_fiestas_patrias() -> None:
    ctx = obtener_calendario(date(2026, 7, 28))
    assert ctx.es_feriado is True
    assert ctx.nombre_feriado == "Fiestas Patrias"
    assert ctx.temporada == "vacacional"


def test_calendario_dia_normal() -> None:
    ctx = obtener_calendario(date(2026, 9, 15))
    assert ctx.es_feriado is False
    assert ctx.nombre_feriado is None
    assert ctx.temporada == "escolar"
    assert ctx.dia_semana == "Martes"


# --- clima_tipico_del_mes (sesion falsa) --------------------------------------


class ResultadoFalso:
    def __init__(self, fila) -> None:
        self._fila = fila

    def first(self):
        return self._fila


class SesionFalsa:
    def __init__(self, fila) -> None:
        self._fila = fila
        self.sentencias: list = []

    async def execute(self, stmt):
        self.sentencias.append(stmt)
        return ResultadoFalso(self._fila)


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


@pytest.mark.asyncio
async def test_clima_tipico_del_mes_filtra_por_lugar_y_mes() -> None:
    sesion = SesionFalsa(("Lluvia ligera", 12, Decimal("20.25")))

    resultado = await visitas.clima_tipico_del_mes(sesion, 42, 3)

    assert resultado == ("Lluvia ligera", 20.3)  # half-up a 1 decimal
    assert len(sesion.sentencias) == 1
    sql = _sql(sesion.sentencias[0])
    assert "visitas_historicas.lugar_id = 42" in sql
    assert "EXTRACT(month FROM visitas_historicas.fecha) = 3" in sql
    assert "GROUP BY visitas_historicas.condicion_clima" in sql
    assert "ORDER BY conteo DESC" in sql
    assert "LIMIT 1" in sql


@pytest.mark.asyncio
async def test_clima_tipico_del_mes_sin_filas_devuelve_none() -> None:
    sesion = SesionFalsa(None)
    assert await visitas.clima_tipico_del_mes(sesion, 42, 11) is None


@pytest.mark.asyncio
async def test_clima_tipico_del_mes_promedio_float() -> None:
    sesion = SesionFalsa(("Soleado", 5, 24.049999))
    assert await visitas.clima_tipico_del_mes(sesion, 1, 7) == ("Soleado", 24.0)

"""Tests del endpoint POST /api/v1/predicciones (SPEC 07) con orquestador stub."""

import logging
from copy import deepcopy
from datetime import date

import httpx
import pytest

from app.api.dependencies import get_orquestador
from app.core.exceptions import (
    AnalistaNoDisponibleError,
    AnalistaRespuestaInvalidaError,
    ContextoNoDisponibleError,
    HistoricosNoDisponiblesError,
)
from app.core.security import create_access_token
from app.main import app
from app.models.prediccion import (
    ContextoPrediccion,
    DiaGrafico,
    HistoricosPrediccion,
    PrediccionResponse,
)

URL = "/api/v1/predicciones"

CONTRATO_200 = {
    "fecha": "2026-09-27",
    "lugar": "Las Manos Cruzadas",
    "contexto": {
        "dia_semana": "Domingo",
        "condicion_clima": "Soleado",
        "temperatura_max": 29.0,
        "fuente_clima": "pronostico",
        "es_feriado": False,
        "nombre_feriado": None,
        "temporada": "escolar",
    },
    "historicos": {
        "cantidad": 8,
        "promedio": 412,
        "minimo": 380,
        "maximo": 450,
        "nivel_coincidencia": 1,
        "dias": [
            {"fecha": "2025-05-11", "visitantes_totales": 380, "condicion_clima": "Soleado"},
            {"fecha": "2025-05-18", "visitantes_totales": 412, "condicion_clima": "Soleado"},
        ],
    },
    "prediccion_estimada": 420,
    "rango_minimo": 390,
    "rango_maximo": 455,
    "fuente_prediccion": "ia",
    "razonamiento_explicado": (
        "Los domingos soleados promedian 412 visitantes; se estima una cifra algo mayor."
    ),
}


RAZONAMIENTO_ESTADISTICO = (
    "Estimación estadística basada en 8 días similares "
    "(el análisis con IA no está disponible)."
)

CONTRATO_200_ESTADISTICA = deepcopy(CONTRATO_200) | {
    "prediccion_estimada": 412,
    "rango_minimo": 380,
    "rango_maximo": 450,
    "fuente_prediccion": "estadistica",
    "razonamiento_explicado": RAZONAMIENTO_ESTADISTICO,
}


def _respuesta_desde(contrato: dict) -> PrediccionResponse:
    historicos = dict(contrato["historicos"])
    dias = [DiaGrafico(**d) for d in historicos.pop("dias")]
    return PrediccionResponse(
        fecha=date.fromisoformat(contrato["fecha"]),
        lugar=contrato["lugar"],
        contexto=ContextoPrediccion(**contrato["contexto"]),
        historicos=HistoricosPrediccion(**historicos, dias=dias),
        prediccion_estimada=contrato["prediccion_estimada"],
        rango_minimo=contrato["rango_minimo"],
        rango_maximo=contrato["rango_maximo"],
        fuente_prediccion=contrato["fuente_prediccion"],
        razonamiento_explicado=contrato["razonamiento_explicado"],
    )


def _respuesta_contrato() -> PrediccionResponse:
    return _respuesta_desde(CONTRATO_200)


class FakeOrq:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.fechas: list[date] = []

    async def predecir(self, fecha: date) -> PrediccionResponse:
        self.fechas.append(fecha)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=app)


@pytest.fixture
def auth_header() -> dict[str, str]:
    token = create_access_token("usuario@practica.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fake_orq():
    """Instala un FakeOrq como override de get_orquestador y lo devuelve."""
    orq = FakeOrq(result=_respuesta_contrato())
    app.dependency_overrides[get_orquestador] = lambda: orq
    yield orq
    app.dependency_overrides.clear()


async def _post(transport, headers=None, json=None, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(URL, headers=headers or {}, json=json, **kwargs)


# --- 200 ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_devuelve_json_exacto_del_contrato(transport, auth_header, fake_orq) -> None:
    response = await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert response.status_code == 200
    assert response.json() == CONTRATO_200
    assert response.json()["fuente_prediccion"] == "ia"


@pytest.mark.asyncio
async def test_200_con_fuente_prediccion_estadistica(transport, auth_header, fake_orq) -> None:
    fake_orq.result = _respuesta_desde(CONTRATO_200_ESTADISTICA)

    response = await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo == CONTRATO_200_ESTADISTICA
    assert cuerpo["fuente_prediccion"] == "estadistica"
    assert cuerpo["prediccion_estimada"] == cuerpo["historicos"]["promedio"]
    assert cuerpo["rango_minimo"] == cuerpo["historicos"]["minimo"]
    assert cuerpo["rango_maximo"] == cuerpo["historicos"]["maximo"]


def test_fuente_prediccion_fuera_de_catalogo_es_invalida() -> None:
    contrato = CONTRATO_200 | {"fuente_prediccion": "otra"}
    with pytest.raises(ValueError):
        _respuesta_desde(contrato)


@pytest.mark.asyncio
async def test_fecha_se_pasa_al_orquestador_como_date(transport, auth_header, fake_orq) -> None:
    await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert fake_orq.fechas == [date(2026, 9, 27)]
    assert type(fake_orq.fechas[0]) is date


# --- 401 ---------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic dXN1YXJpbzpjbGF2ZQ=="},
        {"Authorization": "Bearer token-invalido"},
        {"Authorization": "Bearer "},
    ],
    ids=["sin-token", "basic", "token-invalido", "bearer-vacio"],
)
async def test_401_sin_credenciales_validas(transport, fake_orq, headers) -> None:
    response = await _post(transport, headers, {"fecha": "2026-09-27"})

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert fake_orq.fechas == []


@pytest.mark.asyncio
async def test_401_tiene_prioridad_sobre_body_ausente(transport, fake_orq) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(URL)

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_401_tiene_prioridad_sobre_fecha_invalida(transport, fake_orq) -> None:
    response = await _post(transport, {}, {"fecha": "hola"})

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}


# --- 422 ---------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [{"fecha": "2026-13-01"}, {"fecha": "hola"}, {}, {"otra": "2026-09-27"}],
    ids=["mes-13", "texto", "sin-fecha", "clave-equivocada"],
)
async def test_422_fecha_invalida(transport, auth_header, fake_orq, body) -> None:
    response = await _post(transport, auth_header, body)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    assert any("fecha" in err["loc"] for err in detail)
    assert fake_orq.fechas == []


@pytest.mark.asyncio
async def test_422_sin_body_con_token(transport, auth_header, fake_orq) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(URL, headers=auth_header)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert fake_orq.fechas == []


# --- 502 / 503 ---------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            AnalistaRespuestaInvalidaError("openai devolvio JSON roto"),
            502,
            "El analista devolvió una respuesta inválida.",
        ),
        (
            ContextoNoDisponibleError("weatherapi caido y sin historicos"),
            503,
            "Servicio de predicción no disponible.",
        ),
        (
            HistoricosNoDisponiblesError("sin historicos para Domingo"),
            503,
            "Servicio de predicción no disponible.",
        ),
        (
            AnalistaNoDisponibleError("openai timeout"),
            503,
            "Servicio de predicción no disponible.",
        ),
    ],
    ids=["respuesta-invalida", "contexto", "historicos", "analista-no-disponible"],
)
async def test_errores_de_dominio_se_mapean_sin_filtrar_detalles(
    transport, auth_header, fake_orq, error, status_code, detail
) -> None:
    fake_orq.error = error

    response = await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    cuerpo = response.text.lower()
    assert "openai" not in cuerpo
    assert "weatherapi" not in cuerpo



# --- Logging de 502 / 503 ------------------------------------------------------

SECRETO = "sk-SECRETO-no-loggear"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (AnalistaRespuestaInvalidaError(f"json roto api_key={SECRETO}"), 502),
        (ContextoNoDisponibleError(f"weather ?key={SECRETO}"), 503),
        (HistoricosNoDisponiblesError(f"sin historicos key={SECRETO}"), 503),
        (AnalistaNoDisponibleError(f"openai 429 key={SECRETO}"), 503),
    ],
    ids=["502-respuesta-invalida", "503-contexto", "503-historicos", "503-analista"],
)
async def test_errores_loggean_warning_con_clase_y_fecha_sin_key(
    transport, auth_header, fake_orq, caplog, error, status_code
) -> None:
    fake_orq.error = error
    caplog.set_level(logging.WARNING, logger="app.api.prediccion")

    response = await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert response.status_code == status_code
    registros = [r for r in caplog.records if r.name == "app.api.prediccion"]
    assert len(registros) == 1
    registro = registros[0]
    assert registro.levelno == logging.WARNING
    mensaje = registro.getMessage()
    assert type(error).__name__ in mensaje
    assert "2026-09-27" in mensaje
    assert "key" not in mensaje.lower()
    assert SECRETO not in caplog.text
    assert "key" not in caplog.text.lower()


@pytest.mark.asyncio
async def test_200_no_loggea_warning(transport, auth_header, fake_orq, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="app.api.prediccion")

    response = await _post(transport, auth_header, {"fecha": "2026-09-27"})

    assert response.status_code == 200
    assert not [r for r in caplog.records if r.name == "app.api.prediccion"]

"""Tests del endpoint GET /api/v1/visitas (SPEC 09) con VisitasService stub."""

import logging
from datetime import date

import httpx
import pytest

from app.api.dependencies import get_visitas_service
from app.core.exceptions import FiltrosInvalidosError, HistoricoNoDisponibleError
from app.core.security import create_access_token
from app.main import app
from app.models.visitas import (
    FiltrosVisitas,
    ResumenVisitas,
    VisitaItem,
    VisitasResponse,
)

URL = "/api/v1/visitas"

CONTRATO_200 = {
    "lugar": "Las Manos Cruzadas",
    "filtros": {"fecha": None, "anio": 2025, "mes": 5},
    "orden": "fecha",
    "direccion": "desc",
    "pagina": 1,
    "tamano": 31,
    "total": 31,
    "total_paginas": 1,
    "resumen": {"promedio": 205, "minimo": 41, "maximo": 512, "total_visitantes": 6355},
    "items": [
        {
            "fecha": "2025-05-31",
            "dia_semana": "Sábado",
            "condicion_clima": "Soleado",
            "temperatura_max": 27.4,
            "es_feriado": False,
            "temporada": "escolar",
            "visitantes_totales": 243,
        }
    ],
}

MENSAJE_FECHA_Y_PERIODO = "Usá fecha, o año (con mes opcional), no ambos."
MENSAJE_MES_SIN_ANIO = "El mes requiere un año."


def _respuesta_contrato() -> VisitasResponse:
    c = CONTRATO_200
    return VisitasResponse(
        lugar=c["lugar"],
        filtros=FiltrosVisitas(**c["filtros"]),
        orden=c["orden"],
        direccion=c["direccion"],
        pagina=c["pagina"],
        tamano=c["tamano"],
        total=c["total"],
        total_paginas=c["total_paginas"],
        resumen=ResumenVisitas(**c["resumen"]),
        items=[VisitaItem(**i) for i in c["items"]],
    )


class FakeService:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.llamadas: list[dict] = []

    async def listar(self, **kwargs) -> VisitasResponse:
        self.llamadas.append(kwargs)
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
def fake_service():
    service = FakeService(result=_respuesta_contrato())
    app.dependency_overrides[get_visitas_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


async def _get(transport, headers=None, params=None) -> httpx.Response:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(URL, headers=headers or {}, params=params or {})


# --- 200 ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_devuelve_json_exacto_del_contrato(
    transport, auth_header, fake_service
) -> None:
    response = await _get(transport, auth_header, {"anio": 2025, "mes": 5})

    assert response.status_code == 200
    assert response.json() == CONTRATO_200


@pytest.mark.asyncio
async def test_200_resumen_null_e_items_vacios(transport, auth_header, fake_service) -> None:
    fake_service.result = _respuesta_contrato().model_copy(
        update={"resumen": None, "items": [], "total": 0, "total_paginas": 0}
    )

    response = await _get(transport, auth_header)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["resumen"] is None
    assert cuerpo["items"] == []
    assert cuerpo["total_paginas"] == 0


@pytest.mark.asyncio
async def test_defaults_se_pasan_al_service(transport, auth_header, fake_service) -> None:
    await _get(transport, auth_header)

    assert fake_service.llamadas == [
        {
            "fecha": None,
            "anio": None,
            "mes": None,
            "orden": "fecha",
            "direccion": "desc",
            "pagina": 1,
            "tamano": 31,
        }
    ]


@pytest.mark.asyncio
async def test_parametros_se_pasan_al_service(transport, auth_header, fake_service) -> None:
    await _get(
        transport,
        auth_header,
        {
            "anio": 2024,
            "mes": 12,
            "orden": "visitantes",
            "direccion": "asc",
            "pagina": 3,
            "tamano": 10,
        },
    )

    assert fake_service.llamadas == [
        {
            "fecha": None,
            "anio": 2024,
            "mes": 12,
            "orden": "visitantes",
            "direccion": "asc",
            "pagina": 3,
            "tamano": 10,
        }
    ]


@pytest.mark.asyncio
async def test_fecha_se_pasa_como_date(transport, auth_header, fake_service) -> None:
    await _get(transport, auth_header, {"fecha": "2025-05-31"})

    (llamada,) = fake_service.llamadas
    assert llamada["fecha"] == date(2025, 5, 31)
    assert type(llamada["fecha"]) is date
    assert llamada["anio"] is None and llamada["mes"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"anio": 2000}, {"anio": 2100}, {"tamano": 1}, {"tamano": 100}])
async def test_limites_validos_de_rango(transport, auth_header, fake_service, params) -> None:
    response = await _get(transport, auth_header, params)

    assert response.status_code == 200


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
async def test_401_sin_credenciales_validas(transport, fake_service, headers) -> None:
    response = await _get(transport, headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert fake_service.llamadas == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [{"mes": 13}, {"orden": "otro"}, {"fecha": "hola"}, {"fecha": "2025-01-01", "anio": 2025}],
    ids=["mes-13", "orden-otro", "fecha-invalida", "combinacion-invalida"],
)
async def test_401_tiene_prioridad_sobre_filtros_invalidos(
    transport, fake_service, params
) -> None:
    response = await _get(transport, {}, params)

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert fake_service.llamadas == []


# --- 422 ---------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("mensaje", [MENSAJE_FECHA_Y_PERIODO, MENSAJE_MES_SIN_ANIO])
async def test_422_filtros_invalidos_con_detail_string(
    transport, auth_header, fake_service, mensaje
) -> None:
    fake_service.error = FiltrosInvalidosError(mensaje)

    response = await _get(transport, auth_header, {"mes": 5})

    assert response.status_code == 422
    assert response.json() == {"detail": mensaje}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"orden": "otro"},
        {"direccion": "x"},
        {"mes": 13},
        {"mes": 0},
        {"anio": 1999},
        {"anio": 2101},
        {"tamano": 101},
        {"tamano": 0},
        {"pagina": 0},
        {"fecha": "2025-13-01"},
        {"fecha": "hola"},
        {"anio": "abc"},
    ],
    ids=[
        "orden-otro",
        "direccion-x",
        "mes-13",
        "mes-0",
        "anio-1999",
        "anio-2101",
        "tamano-101",
        "tamano-0",
        "pagina-0",
        "fecha-mes-13",
        "fecha-texto",
        "anio-texto",
    ],
)
async def test_422_formato_estandar_fastapi(
    transport, auth_header, fake_service, params
) -> None:
    response = await _get(transport, auth_header, params)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    (campo,) = params.keys()
    assert detail[0]["loc"] == ["query", campo]
    assert fake_service.llamadas == []


# --- 503 ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_503_historico_no_disponible_y_log_warning(
    transport, auth_header, fake_service, caplog
) -> None:
    fake_service.error = HistoricoNoDisponibleError()
    caplog.set_level(logging.WARNING, logger="app.api.visitas")

    response = await _get(transport, auth_header)

    assert response.status_code == 503
    assert response.json() == {"detail": "Histórico no disponible."}
    registros = [r for r in caplog.records if r.name == "app.api.visitas"]
    assert len(registros) == 1
    assert registros[0].levelno == logging.WARNING
    assert "HistoricoNoDisponibleError" in registros[0].getMessage()

"""Pruebas SPEC 09: VisitasService y queries listar_visitas / resumir_visitas.

Sin Postgres real: las queries se mockean con monkeypatch en `visitas_service`
y el SQL se valida compilando sobre una sesion falsa.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.exceptions import FiltrosInvalidosError, HistoricoNoDisponibleError
from app.db import visitas as db_visitas
from app.models.visitas import (
    EstadisticasVisitas,
    FiltrosVisitas,
    ResumenVisitas,
    VisitaItem,
)
from app.services import visitas_service
from app.services.visitas_service import (
    VisitasService,
    armar_resumen,
    rango_de_fechas,
    validar_filtros,
)

MENSAJE_FECHA_Y_PERIODO = "Usá fecha, o año (con mes opcional), no ambos."
MENSAJE_MES_SIN_ANIO = "El mes requiere un año."
LUGAR = (7, "Las Manos Cruzadas")


def _item(fecha=date(2025, 5, 31), visitantes=243) -> VisitaItem:
    return VisitaItem(
        fecha=fecha,
        dia_semana="Sábado",
        condicion_clima="Soleado",
        temperatura_max=27.4,
        es_feriado=False,
        temporada="escolar",
        visitantes_totales=visitantes,
    )


def _stats(total, suma=None, minimo=None, maximo=None) -> EstadisticasVisitas:
    return EstadisticasVisitas(
        total=total, total_visitantes=suma, minimo=minimo, maximo=maximo
    )


# --- validar_filtros ---------------------------------------------------------


@pytest.mark.parametrize(
    "fecha, anio, mes, mensaje",
    [
        (date(2025, 5, 1), 2025, None, MENSAJE_FECHA_Y_PERIODO),
        (date(2025, 5, 1), None, 5, MENSAJE_FECHA_Y_PERIODO),
        (date(2025, 5, 1), 2025, 5, MENSAJE_FECHA_Y_PERIODO),
        (None, None, 5, MENSAJE_MES_SIN_ANIO),
    ],
    ids=["fecha+anio", "fecha+mes", "fecha+anio+mes", "mes-sin-anio"],
)
def test_validar_filtros_invalidos(fecha, anio, mes, mensaje) -> None:
    with pytest.raises(FiltrosInvalidosError) as exc:
        validar_filtros(fecha, anio, mes)
    assert exc.value.message == mensaje
    assert str(exc.value) == mensaje


@pytest.mark.parametrize(
    "fecha, anio, mes",
    [(None, None, None), (date(2025, 5, 1), None, None), (None, 2025, None), (None, 2025, 5)],
    ids=["sin-filtros", "fecha", "anio", "anio+mes"],
)
def test_validar_filtros_validos(fecha, anio, mes) -> None:
    assert validar_filtros(fecha, anio, mes) is None


# --- rango_de_fechas ---------------------------------------------------------


@pytest.mark.parametrize(
    "fecha, anio, mes, esperado",
    [
        (date(2025, 5, 31), None, None, (date(2025, 5, 31), date(2025, 6, 1))),
        (date(2024, 12, 31), None, None, (date(2024, 12, 31), date(2025, 1, 1))),
        (date(2024, 2, 28), None, None, (date(2024, 2, 28), date(2024, 2, 29))),
        (None, 2025, None, (date(2025, 1, 1), date(2026, 1, 1))),
        (None, 2025, 5, (date(2025, 5, 1), date(2025, 6, 1))),
        (None, 2024, 12, (date(2024, 12, 1), date(2025, 1, 1))),
        (None, 2024, 1, (date(2024, 1, 1), date(2024, 2, 1))),
        (None, None, None, (None, None)),
    ],
    ids=[
        "fecha",
        "fecha-fin-de-anio",
        "fecha-bisiesto",
        "anio",
        "anio+mes",
        "anio+diciembre",
        "anio+enero",
        "sin-filtros",
    ],
)
def test_rango_de_fechas(fecha, anio, mes, esperado) -> None:
    assert rango_de_fechas(fecha, anio, mes) == esperado


# --- armar_resumen -----------------------------------------------------------


@pytest.mark.parametrize(
    "suma, total, promedio",
    [(6355, 31, 205), (5, 2, 3), (7, 2, 4), (1, 3, 0), (2, 3, 1), (10, 4, 3), (9, 4, 2)],
    ids=["contrato", "2.5->3", "3.5->4", "0.33->0", "0.67->1", "2.5-par->3", "2.25->2"],
)
def test_armar_resumen_redondeo_half_up(suma, total, promedio) -> None:
    resumen = armar_resumen(_stats(total, suma, 1, 99))
    assert resumen == ResumenVisitas(
        promedio=promedio, minimo=1, maximo=99, total_visitantes=suma
    )


def test_armar_resumen_total_cero_es_none() -> None:
    assert armar_resumen(_stats(0)) is None


def test_armar_resumen_agregados_none_es_none() -> None:
    assert armar_resumen(_stats(3, None, 1, 2)) is None
    assert armar_resumen(_stats(3, 10, None, 2)) is None
    assert armar_resumen(_stats(3, 10, 1, None)) is None


# --- VisitasService.listar ---------------------------------------------------


class Fakes:
    """Instala dobles de las queries en el modulo del service y registra llamadas."""

    def __init__(self, monkeypatch, *, lugar=LUGAR, stats=None, items=None) -> None:
        self.lugar = lugar
        self.stats = stats if stats is not None else _stats(31, 6355, 41, 512)
        self.items = items if items is not None else [_item()]
        self.lugar_llamadas: list = []
        self.resumir_llamadas: list[dict] = []
        self.listar_llamadas: list[dict] = []
        monkeypatch.setattr(visitas_service, "obtener_lugar_por_codigo", self._lugar)
        monkeypatch.setattr(visitas_service, "resumir_visitas", self._resumir)
        monkeypatch.setattr(visitas_service, "listar_visitas", self._listar)

    async def _lugar(self, session, codigo):
        self.lugar_llamadas.append((session, codigo))
        return self.lugar

    async def _resumir(self, session, **kwargs):
        self.resumir_llamadas.append(kwargs)
        return self.stats

    async def _listar(self, session, **kwargs):
        self.listar_llamadas.append(kwargs)
        return self.items


def _service() -> VisitasService:
    return VisitasService(None, settings=Settings(jwt_secret="x"))


@pytest.mark.asyncio
async def test_listar_respuesta_completa_con_eco(monkeypatch) -> None:
    fakes = Fakes(monkeypatch)

    resp = await _service().listar(anio=2025, mes=5, orden="visitantes", direccion="asc")

    assert resp.lugar == "Las Manos Cruzadas"
    assert resp.filtros == FiltrosVisitas(fecha=None, anio=2025, mes=5)
    assert resp.orden == "visitantes"
    assert resp.direccion == "asc"
    assert resp.pagina == 1
    assert resp.tamano == 31
    assert resp.total == 31
    assert resp.total_paginas == 1
    assert resp.resumen == ResumenVisitas(
        promedio=205, minimo=41, maximo=512, total_visitantes=6355
    )
    assert resp.items == [_item()]
    assert fakes.lugar_llamadas == [(None, "manos-cruzadas")]
    assert fakes.resumir_llamadas == [
        {"lugar_id": 7, "desde": date(2025, 5, 1), "hasta": date(2025, 6, 1)}
    ]
    assert fakes.listar_llamadas == [
        {
            "lugar_id": 7,
            "desde": date(2025, 5, 1),
            "hasta": date(2025, 6, 1),
            "orden": "visitantes",
            "direccion": "asc",
            "limite": 31,
            "offset": 0,
        }
    ]


@pytest.mark.asyncio
async def test_listar_defaults(monkeypatch) -> None:
    fakes = Fakes(monkeypatch)

    resp = await _service().listar()

    assert (resp.orden, resp.direccion, resp.pagina, resp.tamano) == ("fecha", "desc", 1, 31)
    assert resp.filtros == FiltrosVisitas(fecha=None, anio=None, mes=None)
    assert fakes.resumir_llamadas == [{"lugar_id": 7, "desde": None, "hasta": None}]
    assert fakes.listar_llamadas[0]["desde"] is None
    assert fakes.listar_llamadas[0]["hasta"] is None


@pytest.mark.asyncio
async def test_listar_filtro_fecha_pasa_rango_de_un_dia(monkeypatch) -> None:
    fakes = Fakes(monkeypatch, stats=_stats(1, 243, 243, 243))

    resp = await _service().listar(fecha=date(2025, 5, 31))

    assert resp.filtros == FiltrosVisitas(fecha=date(2025, 5, 31), anio=None, mes=None)
    assert fakes.resumir_llamadas == [
        {"lugar_id": 7, "desde": date(2025, 5, 31), "hasta": date(2025, 6, 1)}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pagina, tamano, offset", [(1, 31, 0), (2, 31, 31), (3, 10, 20), (4, 1, 3)]
)
async def test_listar_offset(monkeypatch, pagina, tamano, offset) -> None:
    fakes = Fakes(monkeypatch, stats=_stats(100, 1000, 1, 50))

    await _service().listar(pagina=pagina, tamano=tamano)

    assert fakes.listar_llamadas[0]["limite"] == tamano
    assert fakes.listar_llamadas[0]["offset"] == offset


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "total, tamano, paginas",
    [(31, 31, 1), (32, 31, 2), (62, 31, 2), (63, 31, 3), (1, 100, 1), (100, 1, 100)],
)
async def test_listar_total_paginas_ceil(monkeypatch, total, tamano, paginas) -> None:
    Fakes(monkeypatch, stats=_stats(total, total * 10, 1, 20))

    resp = await _service().listar(tamano=tamano)

    assert resp.total == total
    assert resp.total_paginas == paginas


@pytest.mark.asyncio
async def test_listar_total_cero(monkeypatch) -> None:
    fakes = Fakes(monkeypatch, stats=_stats(0))

    resp = await _service().listar(anio=2030)

    assert resp.total == 0
    assert resp.total_paginas == 0
    assert resp.resumen is None
    assert resp.items == []
    assert fakes.listar_llamadas == []


@pytest.mark.asyncio
async def test_listar_pagina_fuera_de_rango(monkeypatch) -> None:
    fakes = Fakes(monkeypatch, stats=_stats(31, 6355, 41, 512))

    resp = await _service().listar(pagina=2)

    assert resp.items == []
    assert resp.pagina == 2
    assert resp.total_paginas == 1
    # El resumen sigue siendo el del total del filtro, no el de la pagina.
    assert resp.resumen == ResumenVisitas(
        promedio=205, minimo=41, maximo=512, total_visitantes=6355
    )
    assert fakes.listar_llamadas == []


@pytest.mark.asyncio
async def test_listar_ultima_pagina_si_consulta(monkeypatch) -> None:
    fakes = Fakes(monkeypatch, stats=_stats(32, 320, 1, 20))

    await _service().listar(pagina=2)

    assert fakes.listar_llamadas[0]["offset"] == 31


@pytest.mark.asyncio
async def test_listar_lugar_inexistente(monkeypatch) -> None:
    fakes = Fakes(monkeypatch, lugar=None)

    with pytest.raises(HistoricoNoDisponibleError):
        await _service().listar()

    assert fakes.resumir_llamadas == []
    assert fakes.listar_llamadas == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs, mensaje",
    [
        ({"fecha": date(2025, 1, 1), "anio": 2025}, MENSAJE_FECHA_Y_PERIODO),
        ({"fecha": date(2025, 1, 1), "mes": 1}, MENSAJE_FECHA_Y_PERIODO),
        ({"mes": 1}, MENSAJE_MES_SIN_ANIO),
    ],
)
async def test_listar_filtros_invalidos_no_tocan_la_db(monkeypatch, kwargs, mensaje) -> None:
    fakes = Fakes(monkeypatch)

    with pytest.raises(FiltrosInvalidosError) as exc:
        await _service().listar(**kwargs)

    assert exc.value.message == mensaje
    assert fakes.lugar_llamadas == []
    assert fakes.resumir_llamadas == []
    assert fakes.listar_llamadas == []


@pytest.mark.asyncio
async def test_listar_usa_codigo_de_lugar_de_settings(monkeypatch) -> None:
    fakes = Fakes(monkeypatch)
    service = VisitasService(
        None, settings=Settings(jwt_secret="x", prediccion_lugar_codigo="otro-lugar")
    )

    await service.listar()

    assert fakes.lugar_llamadas == [(None, "otro-lugar")]


# --- queries (SQL compilado) -------------------------------------------------


class ResultadoFalso:
    def __init__(self, filas) -> None:
        self._filas = filas

    def all(self):
        return self._filas

    def one(self):
        return self._filas[0]


class SesionFalsa:
    def __init__(self, filas) -> None:
        self._filas = filas
        self.sentencias: list = []

    async def execute(self, stmt):
        self.sentencias.append(stmt)
        return ResultadoFalso(self._filas)


def _sql(stmt) -> str:
    return " ".join(
        str(
            stmt.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        ).split()
    )


FILA = dict(
    fecha=date(2025, 5, 31),
    dia_semana="Sábado",
    condicion_clima="Soleado",
    temperatura_max=27.4,
    es_feriado=False,
    temporada="escolar",
    visitantes_totales=243,
)


async def _listar_sql(**overrides) -> tuple[list[VisitaItem], str]:
    kwargs = dict(
        lugar_id=7,
        desde=date(2025, 5, 1),
        hasta=date(2025, 6, 1),
        orden="fecha",
        direccion="desc",
        limite=31,
        offset=0,
    )
    kwargs.update(overrides)
    sesion = SesionFalsa([SimpleNamespace(_mapping=FILA)])
    items = await db_visitas.listar_visitas(sesion, **kwargs)
    assert len(sesion.sentencias) == 1
    return items, _sql(sesion.sentencias[0])


@pytest.mark.asyncio
async def test_listar_visitas_mapea_filas_a_items() -> None:
    items, _ = await _listar_sql()
    assert items == [VisitaItem(**FILA)]


@pytest.mark.asyncio
async def test_listar_visitas_filtra_lugar_y_rango_semiabierto() -> None:
    _, sql = await _listar_sql()

    assert "visitas_historicas.lugar_id = 7" in sql
    assert "visitas_historicas.fecha >= '2025-05-01'" in sql
    assert "visitas_historicas.fecha < '2025-06-01'" in sql
    assert (
        "visitas_historicas.lugar_id = 7 AND visitas_historicas.fecha >= '2025-05-01' "
        "AND visitas_historicas.fecha < '2025-06-01'"
    ) in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("direccion", ["asc", "desc"])
async def test_listar_visitas_orden_visitantes_con_desempate(direccion) -> None:
    _, sql = await _listar_sql(orden="visitantes", direccion=direccion)

    assert (
        f"ORDER BY visitas_historicas.visitantes_totales {direccion.upper()}, "
        "visitas_historicas.fecha DESC"
    ) in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("direccion", ["asc", "desc"])
async def test_listar_visitas_orden_fecha_sin_desempate(direccion) -> None:
    _, sql = await _listar_sql(orden="fecha", direccion=direccion)

    orden = sql.split("ORDER BY", 1)[1].split("LIMIT", 1)[0].strip()
    assert orden == f"visitas_historicas.fecha {direccion.upper()}"


@pytest.mark.asyncio
async def test_listar_visitas_limit_offset() -> None:
    _, sql = await _listar_sql(limite=10, offset=20)

    assert "LIMIT 10 OFFSET 20" in sql


@pytest.mark.asyncio
async def test_listar_visitas_sin_filtros_de_fecha() -> None:
    _, sql = await _listar_sql(desde=None, hasta=None)

    where = sql.split("WHERE", 1)[1].split("ORDER BY", 1)[0].strip()
    assert where == "visitas_historicas.lugar_id = 7"


def test_columnas_orden_lista_blanca() -> None:
    assert set(db_visitas._COLUMNAS_ORDEN) == {"fecha", "visitantes"}


@pytest.mark.asyncio
async def test_listar_visitas_orden_fuera_de_lista_blanca_falla() -> None:
    with pytest.raises(KeyError):
        await _listar_sql(orden="dia_semana; DROP TABLE x")


@pytest.mark.asyncio
async def test_resumir_visitas_sql_y_resultado() -> None:
    sesion = SesionFalsa([(31, 6355, 41, 512)])

    stats = await db_visitas.resumir_visitas(
        sesion, lugar_id=7, desde=date(2025, 1, 1), hasta=date(2026, 1, 1)
    )

    assert stats == _stats(31, 6355, 41, 512)
    sql = _sql(sesion.sentencias[0])
    assert "count(visitas_historicas.id)" in sql
    assert "sum(visitas_historicas.visitantes_totales)" in sql
    assert "min(visitas_historicas.visitantes_totales)" in sql
    assert "max(visitas_historicas.visitantes_totales)" in sql
    assert "visitas_historicas.lugar_id = 7" in sql
    assert "visitas_historicas.fecha >= '2025-01-01'" in sql
    assert "visitas_historicas.fecha < '2026-01-01'" in sql
    assert "LIMIT" not in sql
    assert "OFFSET" not in sql


@pytest.mark.asyncio
async def test_resumir_visitas_sin_filas() -> None:
    sesion = SesionFalsa([(0, None, None, None)])

    stats = await db_visitas.resumir_visitas(sesion, lugar_id=7, desde=None, hasta=None)

    assert stats == _stats(0)
    where = _sql(sesion.sentencias[0]).split("WHERE", 1)[1].strip()
    assert where == "visitas_historicas.lugar_id = 7"


@pytest.mark.asyncio
async def test_resumir_visitas_total_none_es_cero() -> None:
    sesion = SesionFalsa([(None, None, None, None)])

    stats = await db_visitas.resumir_visitas(sesion, lugar_id=7, desde=None, hasta=None)

    assert stats.total == 0

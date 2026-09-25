"""Pruebas SPEC 05: RAG de historicos (recuperar_historicos, describir_criterios)
y la query buscar_dias_similares.

Sin Postgres real: `buscar_dias_similares` se mockea con monkeypatch en
`rag_historicos` y la query se valida compilando el SQL sobre una sesion falsa.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.exceptions import HistoricosNoDisponiblesError
from app.db import visitas
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    DiaHistorico,
    ResumenHistorico,
)
from app.services.prediccion import rag_historicos
from app.services.prediccion.rag_historicos import (
    describir_criterios,
    recuperar_historicos,
)

LUGAR_ID = 7
FECHA = date(2026, 9, 27)  # domingo
SESSION = object()


def make_settings(**overrides) -> Settings:
    base = {"jwt_secret": "test-secret"}
    base.update(overrides)
    return Settings(**base)


def make_clima(condicion="Soleado", temp=28.0) -> ContextoClima:
    return ContextoClima(
        fecha=FECHA, condicion_clima=condicion, temperatura_max=temp, fuente="pronostico"
    )


def make_calendario(
    dia="Domingo", es_feriado=False, temporada="escolar", nombre=None
) -> ContextoCalendario:
    return ContextoCalendario(
        fecha=FECHA,
        dia_semana=dia,
        es_feriado=es_feriado,
        nombre_feriado=nombre,
        temporada=temporada,
    )


def make_dias(visitantes: list[int], dia="Domingo") -> list[DiaHistorico]:
    return [
        DiaHistorico(
            fecha=FECHA - timedelta(days=7 * (i + 1)),
            dia_semana=dia,
            condicion_clima="Soleado",
            temperatura_max=28.0,
            es_feriado=False,
            temporada="escolar",
            visitantes_totales=v,
        )
        for i, v in enumerate(visitantes)
    ]


class BusquedaFalsa:
    """Reemplazo de buscar_dias_similares: devuelve una respuesta por llamada."""

    def __init__(self, respuestas: list[list[DiaHistorico]]) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list[dict] = []

    async def __call__(self, session, **kwargs):
        self.llamadas.append({"session": session, **kwargs})
        return self.respuestas[len(self.llamadas) - 1]


def instalar(monkeypatch, respuestas) -> BusquedaFalsa:
    falsa = BusquedaFalsa(respuestas)
    monkeypatch.setattr(rag_historicos, "buscar_dias_similares", falsa)
    return falsa


def _opcionales(llamada: dict) -> set[str]:
    return {k for k in ("condicion_clima", "es_feriado", "temporada") if k in llamada}


# --- recuperar_historicos: niveles ------------------------------------------


@pytest.mark.asyncio
async def test_nivel_1_con_8_coincidencias(monkeypatch) -> None:
    visitantes = [412, 380, 450, 400, 420, 410, 415, 409]
    falsa = instalar(monkeypatch, [make_dias(visitantes)])

    resumen = await recuperar_historicos(
        SESSION, LUGAR_ID, make_clima(), make_calendario(), settings=make_settings()
    )

    assert isinstance(resumen, ResumenHistorico)
    assert len(falsa.llamadas) == 1
    assert resumen.nivel_coincidencia == 1
    assert resumen.criterios == ["dia_semana", "condicion_clima", "es_feriado", "temporada"]
    assert resumen.cantidad == 8
    # sum = 3296 / 8 = 412
    assert resumen.promedio == 412
    assert resumen.minimo == 380
    assert resumen.maximo == 450
    assert resumen.resumen_texto == (
        "En los últimos 8 domingos con clima Soleado, el promedio de visitas fue de "
        "412 personas, con un mínimo de 380 y un pico de 450."
    )
    assert resumen.dias == make_dias(visitantes)
    llamada = falsa.llamadas[0]
    assert llamada["condicion_clima"] == "Soleado"
    assert llamada["es_feriado"] is False
    assert llamada["temporada"] == "escolar"


@pytest.mark.asyncio
async def test_cae_a_nivel_3_y_relaja_filtros(monkeypatch) -> None:
    falsa = instalar(
        monkeypatch,
        [make_dias([100]), make_dias([100, 200, 300, 400]), make_dias([10, 20, 30, 40, 50])],
    )

    resumen = await recuperar_historicos(
        SESSION, LUGAR_ID, make_clima(), make_calendario(), settings=make_settings()
    )

    assert len(falsa.llamadas) == 3
    assert _opcionales(falsa.llamadas[0]) == {"condicion_clima", "es_feriado", "temporada"}
    assert _opcionales(falsa.llamadas[1]) == {"condicion_clima", "es_feriado"}
    assert _opcionales(falsa.llamadas[2]) == {"condicion_clima"}
    assert resumen.nivel_coincidencia == 3
    assert resumen.criterios == ["dia_semana", "condicion_clima"]
    assert resumen.cantidad == 5
    assert (resumen.promedio, resumen.minimo, resumen.maximo) == (30, 10, 50)
    assert resumen.resumen_texto == (
        "En los últimos 5 domingos con clima Soleado, el promedio de visitas fue de "
        "30 personas, con un mínimo de 10 y un pico de 50."
    )


@pytest.mark.asyncio
async def test_ningun_nivel_llega_al_minimo_usa_nivel_4(monkeypatch) -> None:
    falsa = instalar(
        monkeypatch, [[], make_dias([1]), make_dias([1]), make_dias([300, 500])]
    )

    resumen = await recuperar_historicos(
        SESSION,
        LUGAR_ID,
        make_clima("Lluvia fuerte"),
        make_calendario(es_feriado=True, temporada="vacacional"),
        settings=make_settings(),
    )

    assert len(falsa.llamadas) == 4
    assert _opcionales(falsa.llamadas[3]) == set()
    assert resumen.nivel_coincidencia == 4
    assert resumen.criterios == ["dia_semana"]
    assert resumen.cantidad == 2
    assert (resumen.promedio, resumen.minimo, resumen.maximo) == (400, 300, 500)
    assert resumen.resumen_texto == (
        "En los últimos 2 domingos, el promedio de visitas fue de "
        "400 personas, con un mínimo de 300 y un pico de 500."
    )


@pytest.mark.asyncio
async def test_tabla_vacia_lanza_historicos_no_disponibles(monkeypatch) -> None:
    falsa = instalar(monkeypatch, [[], [], [], []])

    with pytest.raises(HistoricosNoDisponiblesError):
        await recuperar_historicos(
            SESSION, LUGAR_ID, make_clima(), make_calendario(), settings=make_settings()
        )
    assert len(falsa.llamadas) == 4


@pytest.mark.asyncio
async def test_propaga_fecha_excluida_lugar_y_limite(monkeypatch) -> None:
    falsa = instalar(monkeypatch, [[], [], [], make_dias([5])])
    settings = make_settings(rag_max_resultados=7)

    await recuperar_historicos(
        SESSION, LUGAR_ID, make_clima(temp=21.5), make_calendario(), settings=settings
    )

    for llamada in falsa.llamadas:
        assert llamada["session"] is SESSION
        assert llamada["lugar_id"] == LUGAR_ID
        assert llamada["fecha_excluida"] == FECHA
        assert llamada["dia_semana"] == "Domingo"
        assert llamada["temperatura"] == 21.5
        assert llamada["limite"] == 7


@pytest.mark.asyncio
async def test_limite_por_defecto_es_10_y_min_configurable(monkeypatch) -> None:
    falsa = instalar(monkeypatch, [make_dias([1, 2])])

    resumen = await recuperar_historicos(
        SESSION,
        LUGAR_ID,
        make_clima(),
        make_calendario(),
        settings=make_settings(rag_min_resultados=2),
    )

    assert falsa.llamadas[0]["limite"] == 10
    assert resumen.nivel_coincidencia == 1


@pytest.mark.asyncio
async def test_usa_get_settings_si_no_se_inyecta(monkeypatch) -> None:
    monkeypatch.setattr(rag_historicos, "get_settings", lambda: make_settings())
    instalar(monkeypatch, [make_dias([10] * 5)])

    resumen = await recuperar_historicos(
        SESSION, LUGAR_ID, make_clima(), make_calendario()
    )
    assert resumen.cantidad == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("visitantes", "esperado"),
    [([1, 2], 2), ([1, 2, 2], 2), ([1, 1, 2], 1), ([2, 3], 3), ([10, 11, 11, 11], 11)],
)
async def test_promedio_redondeado_half_up(monkeypatch, visitantes, esperado) -> None:
    instalar(monkeypatch, [make_dias(visitantes)])

    resumen = await recuperar_historicos(
        SESSION,
        LUGAR_ID,
        make_clima(),
        make_calendario(),
        settings=make_settings(rag_min_resultados=1),
    )
    assert resumen.promedio == esperado


# --- describir_criterios -----------------------------------------------------

_VALORES_ESCOLAR = {"condicion_clima": "Soleado", "es_feriado": False, "temporada": "escolar"}
_TODOS = ("condicion_clima", "es_feriado", "temporada")


def test_describir_criterios_feriado_vacacional() -> None:
    valores = {"condicion_clima": "Soleado", "es_feriado": True, "temporada": "vacacional"}
    assert (
        describir_criterios("Domingo", _TODOS, valores)
        == "domingos con clima Soleado, feriados en temporada vacacional"
    )


def test_describir_criterios_no_verbaliza_normales() -> None:
    assert describir_criterios("Domingo", _TODOS, _VALORES_ESCOLAR) == "domingos con clima Soleado"


def test_describir_criterios_filtros_no_aplicados_no_aparecen() -> None:
    valores = {"condicion_clima": "Nublado", "es_feriado": True, "temporada": "vacacional"}
    assert describir_criterios("Domingo", ("condicion_clima",), valores) == "domingos con clima Nublado"
    assert describir_criterios("Domingo", (), valores) == "domingos"


@pytest.mark.parametrize(
    ("dia", "esperado"),
    [
        ("Sábado", "sábados"),
        ("Miércoles", "miércoles"),
        ("Lunes", "lunes"),
        ("Martes", "martes"),
        ("Jueves", "jueves"),
        ("Viernes", "viernes"),
        ("Domingo", "domingos"),
        ("Desconocido", "desconocido"),
    ],
)
def test_describir_criterios_plural_del_dia(dia, esperado) -> None:
    assert describir_criterios(dia, (), _VALORES_ESCOLAR) == esperado


# --- buscar_dias_similares (query) -------------------------------------------


class ResultadoFalso:
    def __init__(self, filas) -> None:
        self._filas = filas

    def all(self):
        return self._filas


class SesionFalsa:
    def __init__(self, filas) -> None:
        self._filas = filas
        self.sentencias: list = []

    async def execute(self, stmt):
        self.sentencias.append(stmt)
        return ResultadoFalso(self._filas)


def _sql(stmt) -> str:
    return str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def _fila(**campos):
    return SimpleNamespace(_mapping=campos)


FILA = dict(
    fecha=date(2025, 5, 18),
    dia_semana="Domingo",
    condicion_clima="Soleado",
    temperatura_max=28.0,
    es_feriado=False,
    temporada="escolar",
    visitantes_totales=412,
)


@pytest.mark.asyncio
async def test_buscar_dias_similares_todos_los_filtros() -> None:
    sesion = SesionFalsa([_fila(**FILA)])

    dias = await visitas.buscar_dias_similares(
        sesion,
        lugar_id=LUGAR_ID,
        fecha_excluida=FECHA,
        dia_semana="Domingo",
        temperatura=27.5,
        condicion_clima="Soleado",
        es_feriado=False,
        temporada="escolar",
        limite=10,
    )

    assert dias == [DiaHistorico(**FILA)]
    assert len(sesion.sentencias) == 1
    sql = _sql(sesion.sentencias[0])
    assert "visitas_historicas.lugar_id = 7" in sql
    assert "visitas_historicas.fecha != '2026-09-27'" in sql
    assert "visitas_historicas.dia_semana = 'Domingo'" in sql
    assert "visitas_historicas.condicion_clima = 'Soleado'" in sql
    assert "visitas_historicas.es_feriado = false" in sql
    assert "visitas_historicas.temporada = 'escolar'" in sql
    assert "ORDER BY abs(visitas_historicas.temperatura_max - 27.5) ASC" in sql
    assert "visitas_historicas.fecha DESC" in sql
    assert sql.index("abs(") < sql.index("fecha DESC")
    assert "LIMIT 10" in sql


@pytest.mark.asyncio
async def test_buscar_dias_similares_filtros_none_no_aparecen() -> None:
    sesion = SesionFalsa([])

    dias = await visitas.buscar_dias_similares(
        sesion,
        lugar_id=LUGAR_ID,
        fecha_excluida=FECHA,
        dia_semana="Sábado",
        temperatura=20,
        limite=3,
    )

    assert dias == []
    sql = _sql(sesion.sentencias[0])
    assert "visitas_historicas.lugar_id = 7" in sql
    assert "visitas_historicas.dia_semana = 'Sábado'" in sql
    where = sql.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "condicion_clima" not in where
    assert "es_feriado" not in where
    assert "temporada" not in where
    assert "LIMIT 3" in sql


@pytest.mark.asyncio
async def test_buscar_dias_similares_es_feriado_true_y_limite_por_defecto() -> None:
    sesion = SesionFalsa([])

    await visitas.buscar_dias_similares(
        sesion,
        lugar_id=1,
        fecha_excluida=FECHA,
        dia_semana="Domingo",
        temperatura=28.0,
        es_feriado=True,
    )

    sql = _sql(sesion.sentencias[0])
    assert "visitas_historicas.es_feriado = true" in sql
    assert "LIMIT 10" in sql

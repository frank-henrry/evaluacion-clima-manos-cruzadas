"""Tests del grafo del orquestador (SPEC 07) con las tools mockeadas."""

import asyncio
import importlib
import logging
from datetime import date

import pytest
from sqlalchemy.dialects import postgresql

from app.api.dependencies import get_orquestador
from app.core.config import get_settings
from app.core.exceptions import (
    AnalistaNoDisponibleError,
    AnalistaRespuestaInvalidaError,
    ContextoNoDisponibleError,
    HistoricosNoDisponiblesError,
)
from app.db.visitas import obtener_lugar_por_codigo
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    DiaHistorico,
    PrediccionLLM,
    PrediccionResponse,
    ResumenHistorico,
)
from app.services.prediccion import orquestador as orq_mod
from app.services.prediccion.orquestador import GRAFO, Orquestador

FECHA = date(2026, 9, 27)

CLIMA = ContextoClima(
    fecha=FECHA, condicion_clima="Soleado", temperatura_max=29.0, fuente="estimado_historico"
)
CALENDARIO = ContextoCalendario(
    fecha=FECHA, dia_semana="Domingo", es_feriado=False, nombre_feriado=None, temporada="escolar"
)
def _dia(fecha: date, visitantes: int, condicion: str = "Soleado") -> DiaHistorico:
    return DiaHistorico(
        fecha=fecha,
        dia_semana="Domingo",
        condicion_clima=condicion,
        temperatura_max=28.5,
        es_feriado=False,
        temporada="escolar",
        visitantes_totales=visitantes,
    )


# Desordenados a proposito: la respuesta debe ordenarlos por fecha ASC.
DIAS_RAG = [
    _dia(date(2025, 6, 1), 450),
    _dia(date(2025, 5, 11), 380, "Parcialmente nublado"),
    _dia(date(2025, 5, 18), 412),
]

HISTORICOS = ResumenHistorico(
    nivel_coincidencia=1,
    criterios=["dia_semana", "condicion_clima"],
    cantidad=8,
    promedio=412,
    minimo=380,
    maximo=450,
    resumen_texto="8 domingos soleados.",
    dias=DIAS_RAG,
)
PREDICCION = PrediccionLLM(
    prediccion_estimada=420,
    rango_minimo=390,
    rango_maximo=455,
    razonamiento_explicado="Los domingos soleados promedian 412 visitantes.",
)


class Registro:
    def __init__(self) -> None:
        self.orden: list[str] = []
        self.args: dict[str, tuple] = {}


@pytest.fixture
def registro(monkeypatch) -> Registro:
    reg = Registro()

    async def fake_lugar(session, codigo):
        reg.orden.append("lugar")
        reg.args["lugar"] = ((session, codigo), {})
        return (1, "Las Manos Cruzadas")

    async def fake_clima(*args, **kwargs):
        # Cede el control para que calendario termine antes: rag debe esperar igual.
        await asyncio.sleep(0.01)
        reg.orden.append("clima")
        reg.args["clima"] = (args, kwargs)
        return CLIMA

    def fake_calendario(*args, **kwargs):
        reg.orden.append("calendario")
        reg.args["calendario"] = (args, kwargs)
        return CALENDARIO

    async def fake_rag(*args, **kwargs):
        reg.orden.append("rag")
        reg.args["rag"] = (args, kwargs)
        return HISTORICOS

    async def fake_analizar(*args, **kwargs):
        reg.orden.append("analista")
        reg.args["analista"] = (args, kwargs)
        return PREDICCION

    monkeypatch.setattr(orq_mod, "obtener_lugar_por_codigo", fake_lugar)
    monkeypatch.setattr(orq_mod, "obtener_clima", fake_clima)
    monkeypatch.setattr(orq_mod, "obtener_calendario", fake_calendario)
    monkeypatch.setattr(orq_mod, "recuperar_historicos", fake_rag)
    monkeypatch.setattr(orq_mod, "analizar", fake_analizar)
    return reg


SESSION = object()
WEATHER = object()
LLM = object()


def _orquestador() -> Orquestador:
    return Orquestador(SESSION, WEATHER, llm=LLM, settings=get_settings())


@pytest.mark.asyncio
async def test_clima_y_calendario_antes_de_rag_y_rag_antes_de_analista(registro) -> None:
    await _orquestador().predecir(FECHA)

    assert registro.orden[0] == "lugar"
    assert set(registro.orden[1:3]) == {"clima", "calendario"}
    assert registro.orden[3:] == ["rag", "analista"]


@pytest.mark.asyncio
async def test_argumentos_propagados_a_las_tools(registro) -> None:
    settings = get_settings()
    await _orquestador().predecir(FECHA)

    assert registro.args["lugar"][0] == (SESSION, settings.prediccion_lugar_codigo)

    args, kwargs = registro.args["clima"]
    assert args == (FECHA, SESSION, WEATHER)
    assert kwargs["lugar_id"] == 1
    assert kwargs["settings"] is settings

    assert registro.args["calendario"][0] == (FECHA,)

    args, kwargs = registro.args["rag"]
    assert args == (SESSION, 1, CLIMA, CALENDARIO)
    assert kwargs["settings"] is settings

    args, kwargs = registro.args["analista"]
    assert args == (FECHA, CLIMA, CALENDARIO, HISTORICOS, LLM)
    assert kwargs["settings"] is settings


@pytest.mark.asyncio
async def test_respuesta_mapea_fuente_a_fuente_clima_y_lugar(registro) -> None:
    respuesta = await _orquestador().predecir(FECHA)

    assert isinstance(respuesta, PrediccionResponse)
    assert respuesta.model_dump(mode="json") == {
        "fecha": "2026-09-27",
        "lugar": "Las Manos Cruzadas",
        "contexto": {
            "dia_semana": "Domingo",
            "condicion_clima": "Soleado",
            "temperatura_max": 29.0,
            "fuente_clima": "estimado_historico",
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
                {
                    "fecha": "2025-05-11",
                    "visitantes_totales": 380,
                    "condicion_clima": "Parcialmente nublado",
                },
                {"fecha": "2025-05-18", "visitantes_totales": 412, "condicion_clima": "Soleado"},
                {"fecha": "2025-06-01", "visitantes_totales": 450, "condicion_clima": "Soleado"},
            ],
        },
        "prediccion_estimada": 420,
        "rango_minimo": 390,
        "rango_maximo": 455,
        "fuente_prediccion": "ia",
        "razonamiento_explicado": "Los domingos soleados promedian 412 visitantes.",
    }


@pytest.mark.asyncio
async def test_lugar_inexistente_lanza_contexto_no_disponible_sin_llamar_tools(
    registro, monkeypatch
) -> None:
    async def sin_lugar(session, codigo):
        registro.orden.append("lugar")
        return None

    monkeypatch.setattr(orq_mod, "obtener_lugar_por_codigo", sin_lugar)

    with pytest.raises(ContextoNoDisponibleError):
        await _orquestador().predecir(FECHA)
    assert registro.orden == ["lugar"]


@pytest.mark.asyncio
async def test_error_de_rag_se_propaga_y_no_llama_analista(registro, monkeypatch) -> None:
    async def rag_falla(*args, **kwargs):
        registro.orden.append("rag")
        raise HistoricosNoDisponiblesError("sin historicos")

    monkeypatch.setattr(orq_mod, "recuperar_historicos", rag_falla)

    with pytest.raises(HistoricosNoDisponiblesError):
        await _orquestador().predecir(FECHA)
    assert "analista" not in registro.orden


@pytest.mark.asyncio
async def test_error_de_analista_se_propaga(registro, monkeypatch) -> None:
    async def analista_falla(*args, **kwargs):
        raise AnalistaRespuestaInvalidaError("json roto")

    monkeypatch.setattr(orq_mod, "analizar", analista_falla)

    with pytest.raises(AnalistaRespuestaInvalidaError):
        await _orquestador().predecir(FECHA)


@pytest.mark.asyncio
async def test_error_de_clima_se_propaga_sin_llegar_a_rag(registro, monkeypatch) -> None:
    async def clima_falla(*args, **kwargs):
        raise ContextoNoDisponibleError("sin clima")

    monkeypatch.setattr(orq_mod, "obtener_clima", clima_falla)

    with pytest.raises(ContextoNoDisponibleError):
        await _orquestador().predecir(FECHA)
    assert "rag" not in registro.orden


@pytest.mark.asyncio
async def test_grafo_compilado_una_sola_vez(registro) -> None:
    grafo_antes = orq_mod.GRAFO
    await _orquestador().predecir(FECHA)
    await _orquestador().predecir(date(2026, 9, 28))

    assert orq_mod.GRAFO is grafo_antes is GRAFO
    assert set(GRAFO.get_graph().nodes) >= {"clima", "calendario", "rag", "analista"}


def test_settings_por_defecto_es_get_settings() -> None:
    orq = Orquestador(SESSION, WEATHER)
    assert orq._settings is get_settings()
    assert orq._llm is None


# --- obtener_lugar_por_codigo ------------------------------------------------


class _Result:
    def __init__(self, fila) -> None:
        self._fila = fila

    def first(self):
        return self._fila


class FakeSession:
    def __init__(self, fila) -> None:
        self._fila = fila
        self.stmts: list = []

    async def execute(self, stmt):
        self.stmts.append(stmt)
        return _Result(self._fila)


def _sql(stmt) -> str:
    return str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


@pytest.mark.asyncio
async def test_obtener_lugar_por_codigo_filtra_por_codigo_y_devuelve_tupla() -> None:
    session = FakeSession(fila=("7", "Las Manos Cruzadas"))

    lugar = await obtener_lugar_por_codigo(session, "manos-cruzadas")

    assert lugar == (7, "Las Manos Cruzadas")
    assert isinstance(lugar[0], int)
    sql = _sql(session.stmts[0])
    assert "lugar_turistico.codigo = 'manos-cruzadas'" in sql
    assert "lugar_turistico.id" in sql and "lugar_turistico.nombre" in sql


@pytest.mark.asyncio
async def test_obtener_lugar_por_codigo_sin_filas_devuelve_none() -> None:
    session = FakeSession(fila=None)

    assert await obtener_lugar_por_codigo(session, "no-existe") is None
    assert len(session.stmts) == 1


# --- get_orquestador ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orquestador_construye_orquestador_con_la_sesion() -> None:
    session = object()

    orq = await get_orquestador(session=session)

    assert isinstance(orq, Orquestador)
    assert orq._session is session
    assert orq._settings is get_settings()
    assert orq._llm is None



# --- Respaldo estadistico y fuente_prediccion -----------------------------------

RAZONAMIENTO_ESTADISTICO = (
    "Estimación estadística basada en 8 días similares "
    "(el análisis con IA no está disponible)."
)
SECRETO = "sk-SECRETO-no-loggear"


@pytest.fixture
def analista_no_disponible(registro, monkeypatch):
    async def analista_caido(*args, **kwargs):
        registro.orden.append("analista")
        raise AnalistaNoDisponibleError(f"openai 429 api_key={SECRETO}")

    monkeypatch.setattr(orq_mod, "analizar", analista_caido)
    return registro


@pytest.mark.asyncio
async def test_llm_ok_marca_fuente_prediccion_ia(registro) -> None:
    respuesta = await _orquestador().predecir(FECHA)

    assert respuesta.fuente_prediccion == "ia"
    assert respuesta.prediccion_estimada == PREDICCION.prediccion_estimada
    assert respuesta.rango_minimo == PREDICCION.rango_minimo
    assert respuesta.rango_maximo == PREDICCION.rango_maximo
    assert respuesta.razonamiento_explicado == PREDICCION.razonamiento_explicado


@pytest.mark.asyncio
async def test_analista_no_disponible_usa_respaldo_estadistico(analista_no_disponible) -> None:
    respuesta = await _orquestador().predecir(FECHA)

    assert analista_no_disponible.orden[-1] == "analista"
    assert respuesta.fuente_prediccion == "estadistica"
    assert respuesta.prediccion_estimada == HISTORICOS.promedio == 412
    assert respuesta.rango_minimo == HISTORICOS.minimo == 380
    assert respuesta.rango_maximo == HISTORICOS.maximo == 450
    assert respuesta.razonamiento_explicado == RAZONAMIENTO_ESTADISTICO
    # El resto de la respuesta no cambia.
    assert respuesta.historicos.cantidad == 8
    assert [d.fecha for d in respuesta.historicos.dias] == sorted(d.fecha for d in DIAS_RAG)
    assert respuesta.contexto.condicion_clima == "Soleado"


@pytest.mark.asyncio
async def test_respaldo_usa_la_cantidad_real_de_historicos(registro, monkeypatch) -> None:
    historicos = HISTORICOS.model_copy(
        update={"cantidad": 3, "promedio": 100, "minimo": 90, "maximo": 130}
    )

    async def fake_rag(*args, **kwargs):
        return historicos

    async def analista_caido(*args, **kwargs):
        raise AnalistaNoDisponibleError("sin key")

    monkeypatch.setattr(orq_mod, "recuperar_historicos", fake_rag)
    monkeypatch.setattr(orq_mod, "analizar", analista_caido)

    respuesta = await _orquestador().predecir(FECHA)

    assert (respuesta.prediccion_estimada, respuesta.rango_minimo, respuesta.rango_maximo) == (
        100,
        90,
        130,
    )
    assert respuesta.razonamiento_explicado == (
        "Estimación estadística basada en 3 días similares "
        "(el análisis con IA no está disponible)."
    )
    assert respuesta.fuente_prediccion == "estadistica"


def test_respaldo_estadistico_directo() -> None:
    prediccion = orq_mod.respaldo_estadistico(HISTORICOS)

    assert prediccion == PrediccionLLM(
        prediccion_estimada=412,
        rango_minimo=380,
        rango_maximo=450,
        razonamiento_explicado=RAZONAMIENTO_ESTADISTICO,
    )


@pytest.mark.asyncio
async def test_respuesta_invalida_no_activa_respaldo(registro, monkeypatch, caplog) -> None:
    async def analista_invalido(*args, **kwargs):
        raise AnalistaRespuestaInvalidaError("json roto")

    monkeypatch.setattr(orq_mod, "analizar", analista_invalido)
    caplog.set_level(logging.WARNING, logger=orq_mod.__name__)

    with pytest.raises(AnalistaRespuestaInvalidaError):
        await _orquestador().predecir(FECHA)
    assert "respaldo" not in caplog.text.lower()


@pytest.mark.asyncio
async def test_respaldo_loggea_warning_con_fecha_y_clase_sin_key(
    analista_no_disponible, caplog
) -> None:
    caplog.set_level(logging.WARNING, logger=orq_mod.__name__)

    await _orquestador().predecir(FECHA)

    warnings = [
        r
        for r in caplog.records
        if r.name == orq_mod.__name__ and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    mensaje = warnings[0].getMessage()
    assert "2026-09-27" in mensaje
    assert "AnalistaNoDisponibleError" in mensaje
    assert "key" not in mensaje.lower()
    assert SECRETO not in caplog.text
    assert "key" not in caplog.text.lower()


@pytest.mark.asyncio
async def test_historicos_dias_ordenados_asc_y_solo_tres_campos(registro) -> None:
    respuesta = await _orquestador().predecir(FECHA)

    dias = respuesta.model_dump(mode="json")["historicos"]["dias"]
    assert [d["fecha"] for d in dias] == ["2025-05-11", "2025-05-18", "2025-06-01"]
    for dia in dias:
        assert set(dia) == {"fecha", "visitantes_totales", "condicion_clima"}
    assert dias[0] == {
        "fecha": "2025-05-11",
        "visitantes_totales": 380,
        "condicion_clima": "Parcialmente nublado",
    }
    # El RAG no se muta: sigue en su orden original.
    assert [d.fecha for d in HISTORICOS.dias] == [d.fecha for d in DIAS_RAG]


def test_logger_httpx_queda_en_warning_tras_importar_main() -> None:
    importlib.import_module("app.main")

    httpx_logger = logging.getLogger("httpx")
    assert httpx_logger.level == logging.WARNING
    assert not httpx_logger.isEnabledFor(logging.INFO)

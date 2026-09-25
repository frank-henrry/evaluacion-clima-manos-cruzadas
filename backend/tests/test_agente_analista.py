"""Pruebas SPEC 06: Agente Analista (analizar, construir_mensajes, PrediccionLLM).

Ningun test llama a la API real de OpenAI: el LLM se inyecta como un stub
duck-typed (`FakeLLM`) y, cuando se prueba la construccion desde la config,
`langchain_openai.ChatOpenAI` se reemplaza con monkeypatch.
"""

import asyncio
import logging
from datetime import date

import httpx
import openai
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    AnalistaNoDisponibleError,
    AnalistaRespuestaInvalidaError,
)
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    DiaHistorico,
    PrediccionLLM,
    ResumenHistorico,
)
from app.services.prediccion.agente_analista import analizar
from app.services.prediccion.prompts import (
    SIN_FERIADO,
    SYSTEM_PROMPT,
    construir_mensajes,
)

FECHA = date(2026, 9, 27)  # domingo
FAKE_KEY = "sk-test-NO-REAL-KEY-1234567890"
RESUMEN = "Se encontraron 6 domingos soleados en temporada escolar; promedio 412."

RESPUESTA_OK = {
    "prediccion_estimada": 420,
    "rango_minimo": 390,
    "rango_maximo": 455,
    "razonamiento_explicado": "Los domingos soleados promedian 412 visitantes.",
}


class FakeLLM:
    """LLM falso: registra el schema y los mensajes; devuelve o lanza `resultado`."""

    def __init__(self, resultado) -> None:
        self.resultado = resultado
        self.mensajes = None
        self.schema = None

    def with_structured_output(self, schema, **kw):
        self.schema = schema

        async def _run(mensajes):
            self.mensajes = mensajes
            if isinstance(self.resultado, BaseException):
                raise self.resultado
            return self.resultado

        return RunnableLambda(lambda m: None, afunc=_run)


def make_settings(**overrides) -> Settings:
    base = {"jwt_secret": "x", "openai_api_key": ""}
    base.update(overrides)
    return Settings(**base)


def make_clima(fuente="pronostico") -> ContextoClima:
    return ContextoClima(
        fecha=FECHA, condicion_clima="Soleado", temperatura_max=28.0, fuente=fuente
    )


def make_calendario(nombre=None, es_feriado=False) -> ContextoCalendario:
    return ContextoCalendario(
        fecha=FECHA,
        dia_semana="Domingo",
        es_feriado=es_feriado,
        nombre_feriado=nombre,
        temporada="escolar",
    )


def make_historicos(nivel=1, resumen=RESUMEN) -> ResumenHistorico:
    dia = DiaHistorico(
        fecha=date(2026, 9, 20),
        dia_semana="Domingo",
        condicion_clima="Soleado",
        temperatura_max=28.0,
        es_feriado=False,
        temporada="escolar",
        visitantes_totales=412,
    )
    return ResumenHistorico(
        nivel_coincidencia=nivel,
        criterios=["dia_semana", "condicion_clima", "temporada"],
        cantidad=1,
        promedio=412,
        minimo=412,
        maximo=412,
        resumen_texto=resumen,
        dias=[dia],
    )


async def correr(llm, **kwargs):
    return await analizar(
        FECHA,
        kwargs.pop("clima", make_clima()),
        kwargs.pop("calendario", make_calendario()),
        kwargs.pop("historicos", make_historicos()),
        llm,
        **kwargs,
    )


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://x")


# --- Respuesta valida --------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resultado", [RESPUESTA_OK, PrediccionLLM(**RESPUESTA_OK)], ids=["dict", "modelo"]
)
async def test_respuesta_valida_devuelve_prediccion(resultado):
    llm = FakeLLM(resultado)

    pred = await correr(llm)

    assert isinstance(pred, PrediccionLLM)
    assert pred.model_dump() == RESPUESTA_OK
    assert llm.schema is PrediccionLLM


@pytest.mark.asyncio
async def test_llm_inyectado_no_consulta_settings_ni_construye_chatopenai(monkeypatch):
    import langchain_openai

    def _no_llamar(*a, **kw):  # pragma: no cover - solo falla si se llama
        raise AssertionError("ChatOpenAI no debe construirse con llm inyectado")

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _no_llamar)

    pred = await correr(FakeLLM(RESPUESTA_OK), settings=make_settings())

    assert pred.prediccion_estimada == 420


# --- Respuesta invalida ------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cambios",
    [
        {"rango_minimo": 430},  # min > estimada
        {"rango_maximo": 400},  # estimada > max
        {"prediccion_estimada": -1, "rango_minimo": -5},
        {"rango_minimo": -1},
        {"razonamiento_explicado": ""},
        {"razonamiento_explicado": "a" * 1001},
    ],
    ids=[
        "min_mayor_que_estimada",
        "estimada_mayor_que_max",
        "estimada_negativa",
        "minimo_negativo",
        "razonamiento_vacio",
        "razonamiento_largo",
    ],
)
async def test_respuesta_fuera_de_contrato_es_invalida(cambios):
    llm = FakeLLM({**RESPUESTA_OK, **cambios})

    with pytest.raises(AnalistaRespuestaInvalidaError) as exc_info:
        await correr(llm)

    assert isinstance(exc_info.value.__cause__, ValidationError)


@pytest.mark.asyncio
async def test_modelo_construido_sin_validar_se_revalida():
    invalido = PrediccionLLM.model_construct(**{**RESPUESTA_OK, "rango_minimo": 999})

    with pytest.raises(AnalistaRespuestaInvalidaError):
        await correr(FakeLLM(invalido))


@pytest.mark.asyncio
@pytest.mark.parametrize("resultado", [None, "420", 420, [RESPUESTA_OK]])
async def test_resultado_con_tipo_inesperado_es_invalido(resultado):
    with pytest.raises(AnalistaRespuestaInvalidaError):
        await correr(FakeLLM(resultado))


@pytest.mark.asyncio
async def test_campos_faltantes_es_invalido():
    with pytest.raises(AnalistaRespuestaInvalidaError):
        await correr(FakeLLM({"prediccion_estimada": 420}))


@pytest.mark.asyncio
async def test_output_parser_exception_es_invalida():
    with pytest.raises(AnalistaRespuestaInvalidaError):
        await correr(FakeLLM(OutputParserException("json roto")))


@pytest.mark.asyncio
async def test_length_finish_reason_es_invalida():
    exc = openai.LengthFinishReasonError.__new__(openai.LengthFinishReasonError)
    Exception.__init__(exc, "cortado")

    with pytest.raises(AnalistaRespuestaInvalidaError):
        await correr(FakeLLM(exc))


# --- LLM no disponible -------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        TimeoutError(),
        asyncio.TimeoutError(),
        openai.APITimeoutError(request=_request()),
        openai.APIConnectionError(request=_request()),
        openai.APIStatusError(
            "boom",
            response=httpx.Response(500, request=_request()),
            body=None,
        ),
    ],
    ids=["timeout", "asyncio_timeout", "api_timeout", "api_connection", "api_status_500"],
)
async def test_errores_de_red_son_no_disponible(error):
    with pytest.raises(AnalistaNoDisponibleError) as exc_info:
        await correr(FakeLLM(error))

    assert exc_info.value.__cause__ is error


@pytest.mark.asyncio
async def test_error_ajeno_se_propaga_sin_traducir():
    with pytest.raises(RuntimeError, match="bug"):
        await correr(FakeLLM(RuntimeError("bug")))


# --- Key vacia / construccion de ChatOpenAI ----------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["", "   "], ids=["vacia", "solo_espacios"])
async def test_key_vacia_no_llama_a_openai(monkeypatch, key):
    import langchain_openai

    llamadas: list = []

    def _no_llamar(*a, **kw):
        llamadas.append((a, kw))
        raise AssertionError("ChatOpenAI no debe construirse sin key")

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _no_llamar)

    with pytest.raises(AnalistaNoDisponibleError):
        await correr(None, settings=make_settings(openai_api_key=key))

    assert llamadas == []


@pytest.mark.asyncio
async def test_key_presente_construye_chatopenai_desde_config(monkeypatch, caplog):
    import langchain_openai

    registro: dict = {}
    fake = FakeLLM(RESPUESTA_OK)

    class FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            registro.update(kwargs)

        def with_structured_output(self, schema, **kw):
            return fake.with_structured_output(schema, **kw)

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChatOpenAI)
    settings = make_settings(
        openai_api_key=FAKE_KEY,
        openai_model="modelo-de-test",
        openai_temperature=0.7,
        openai_timeout_seconds=9.5,
    )

    with caplog.at_level(logging.DEBUG):
        pred = await correr(None, settings=settings)

    assert pred.model_dump() == RESPUESTA_OK
    assert fake.schema is PrediccionLLM
    assert registro["model"] == "modelo-de-test"
    assert registro["temperature"] == 0.7
    assert registro["timeout"] == 9.5
    assert registro["max_retries"] == 1
    api_key = registro["api_key"]
    valor = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else api_key
    assert valor == FAKE_KEY
    assert FAKE_KEY not in caplog.text


# --- Mensajes ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_mensajes_enviados_al_llm():
    llm = FakeLLM(RESPUESTA_OK)

    await correr(
        llm,
        clima=make_clima(fuente="estimado_historico"),
        historicos=make_historicos(nivel=3),
    )

    sistema, usuario = llm.mensajes
    assert isinstance(sistema, SystemMessage)
    assert sistema.content == SYSTEM_PROMPT
    assert "Las Manos Cruzadas" in sistema.content
    assert isinstance(usuario, HumanMessage)
    assert RESUMEN in usuario.content
    assert "(fuente: estimado_historico)" in usuario.content
    assert "Es Domingo." in usuario.content
    assert "2026-09-27" in usuario.content
    assert "(nivel 3)" in usuario.content
    assert "Temporada: escolar." in usuario.content
    assert "28.0" in usuario.content and "Soleado" in usuario.content


def test_nombre_feriado_none_se_muestra_como_ninguno():
    _, usuario = construir_mensajes(
        FECHA, make_clima(), make_calendario(nombre=None), make_historicos()
    )

    assert SIN_FERIADO == "ninguno"
    assert "Feriado/fiesta: ninguno." in usuario.content


def test_nombre_feriado_presente_se_incluye():
    _, usuario = construir_mensajes(
        FECHA,
        make_clima(),
        make_calendario(nombre="Aniversario de Huanuco", es_feriado=True),
        make_historicos(),
    )

    assert "Feriado/fiesta: Aniversario de Huanuco." in usuario.content
    assert "ninguno" not in usuario.content


# --- Logs --------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resultado",
    [RESPUESTA_OK, {**RESPUESTA_OK, "rango_minimo": 999}, TimeoutError()],
    ids=["ok", "invalida", "timeout"],
)
async def test_logs_no_contienen_prompt_ni_key(caplog, resultado):
    with caplog.at_level(logging.DEBUG):
        try:
            await correr(FakeLLM(resultado), settings=make_settings(openai_api_key=FAKE_KEY))
        except (AnalistaNoDisponibleError, AnalistaRespuestaInvalidaError):
            pass

    registros = [
        r for r in caplog.records if r.name == "app.services.prediccion.agente_analista"
    ]
    assert registros, "se esperaba al menos un log del agente"
    texto = caplog.text
    assert FECHA.isoformat() in texto
    assert FAKE_KEY not in texto
    assert RESUMEN not in texto
    assert "Las Manos Cruzadas" not in texto
    assert "Contexto actual" not in texto
    assert "latencia_ms=" in texto


# --- PrediccionLLM -----------------------------------------------------------


def test_prediccion_llm_acepta_rango_degenerado():
    pred = PrediccionLLM(
        prediccion_estimada=0, rango_minimo=0, rango_maximo=0, razonamiento_explicado="x"
    )
    assert pred.rango_minimo == pred.prediccion_estimada == pred.rango_maximo == 0

    pred = PrediccionLLM(
        prediccion_estimada=100,
        rango_minimo=100,
        rango_maximo=100,
        razonamiento_explicado="a" * 1000,
    )
    assert pred.prediccion_estimada == 100


@pytest.mark.parametrize(
    "cambios",
    [{"rango_minimo": 421}, {"rango_maximo": 419}, {"rango_maximo": -1}],
)
def test_prediccion_llm_rechaza_rangos_incoherentes(cambios):
    with pytest.raises(ValidationError):
        PrediccionLLM(**{**RESPUESTA_OK, **cambios})

"""Agente Analista (SPEC 06): el LLM evalua contexto + historicos y predice.

- El LLM es inyectable (`llm`); si llega `None` se construye `ChatOpenAI` desde
  la config. Con `OPENAI_API_KEY` vacia se lanza `AnalistaNoDisponibleError`
  sin construir ni llamar al cliente.
- La salida se pide con `with_structured_output(PrediccionLLM)` y se revalida.
- Solo se registran la fecha y la latencia: nunca la key ni el prompt.

No conoce HTTP ni FastAPI.
"""

import logging
import time
from datetime import date

import openai
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AnalistaNoDisponibleError,
    AnalistaRespuestaInvalidaError,
)
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    PrediccionLLM,
    ResumenHistorico,
)
from app.services.prediccion.prompts import construir_mensajes

logger = logging.getLogger(__name__)

# Errores de OpenAI que significan "la API respondio, pero la salida no sirve"
# (corte por longitud o filtro de contenido): se tratan como respuesta invalida.
_OPENAI_SALIDA_INVALIDA: tuple[type[Exception], ...] = (
    openai.LengthFinishReasonError,
    openai.ContentFilterFinishReasonError,
)

try:  # El modelo rechazo responder con el schema (solo con method="json_schema").
    from langchain_openai.chat_models.base import OpenAIRefusalError

    _OPENAI_SALIDA_INVALIDA += (OpenAIRefusalError,)
except ImportError:  # pragma: no cover - depende de la version de langchain-openai
    pass


def _construir_llm(cfg: Settings) -> BaseChatModel:
    """`ChatOpenAI` segun la config. Lanza `AnalistaNoDisponibleError` si no hay key."""
    api_key = cfg.openai_api_key.get_secret_value().strip()
    if not api_key:
        raise AnalistaNoDisponibleError("El agente analista no esta configurado.")

    from langchain_openai import ChatOpenAI  # import diferido: solo si se usa

    return ChatOpenAI(
        model=cfg.openai_model,
        temperature=cfg.openai_temperature,
        timeout=cfg.openai_timeout_seconds,
        max_retries=1,
        api_key=cfg.openai_api_key,
    )


def _a_prediccion(resultado: object) -> PrediccionLLM:
    """Normaliza la salida estructurada a `PrediccionLLM` (revalidando siempre)."""
    if isinstance(resultado, PrediccionLLM):
        # Revalida por si el LLM falso/real construyo la instancia sin validar
        # (p. ej. `model_construct`).
        return PrediccionLLM.model_validate(resultado.model_dump())
    if isinstance(resultado, dict):
        return PrediccionLLM.model_validate(resultado)
    raise AnalistaRespuestaInvalidaError(
        "El agente analista devolvio una respuesta con formato inesperado."
    )


async def analizar(
    fecha: date,
    clima: ContextoClima,
    calendario: ContextoCalendario,
    historicos: ResumenHistorico,
    llm: BaseChatModel | None = None,
    *,
    settings: Settings | None = None,
) -> PrediccionLLM:
    """Pide al LLM una prediccion de visitantes para `fecha`.

    Firma del SPEC 06 ampliada con `settings` keyword-only (inyectable en tests;
    por defecto `get_settings()`). Si se inyecta `llm`, la key no se consulta.

    Raises:
        AnalistaNoDisponibleError: key vacia (sin llamar a OpenAI), timeout,
            error de conexion o cualquier error de la API de OpenAI.
        AnalistaRespuestaInvalidaError: la salida no cumple `PrediccionLLM`
            (schema, rangos, `None`, tipo inesperado, rechazo del modelo o
            respuesta cortada por longitud/filtro de contenido).

    Cualquier otra excepcion (p. ej. un bug de programacion o un error propio de
    un LLM falso) se propaga sin traducir para no enmascararla.
    """
    if llm is None:
        llm = _construir_llm(settings or get_settings())

    mensajes = construir_mensajes(fecha, clima, calendario, historicos)
    estructurado = llm.with_structured_output(PrediccionLLM)

    inicio = time.perf_counter()
    try:
        resultado = await estructurado.ainvoke(mensajes)
        prediccion = _a_prediccion(resultado)
    except AnalistaRespuestaInvalidaError:
        logger.warning(
            "Agente analista: respuesta invalida fecha=%s latencia_ms=%d",
            fecha.isoformat(),
            _ms_desde(inicio),
        )
        raise
    except (ValidationError, OutputParserException, *_OPENAI_SALIDA_INVALIDA) as exc:
        logger.warning(
            "Agente analista: respuesta invalida fecha=%s latencia_ms=%d",
            fecha.isoformat(),
            _ms_desde(inicio),
        )
        raise AnalistaRespuestaInvalidaError(
            "El agente analista devolvio una respuesta invalida."
        ) from exc
    except (TimeoutError, openai.OpenAIError) as exc:
        # `asyncio.TimeoutError` es alias de `TimeoutError` desde Python 3.11.
        # `openai.OpenAIError` cubre APIError, APITimeoutError y APIConnectionError.
        logger.warning(
            "Agente analista no disponible fecha=%s latencia_ms=%d error=%s",
            fecha.isoformat(),
            _ms_desde(inicio),
            type(exc).__name__,
        )
        raise AnalistaNoDisponibleError("El agente analista no esta disponible.") from exc

    logger.info(
        "Agente analista OK fecha=%s latencia_ms=%d",
        fecha.isoformat(),
        _ms_desde(inicio),
    )
    return prediccion


def _ms_desde(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)

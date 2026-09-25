"""Orquestador de la prediccion de visitantes (SPEC 07).

Grafo LangGraph compilado UNA sola vez al importar el modulo (`GRAFO`):

    START -> clima ------\\
                          +--> rag -> analista -> END
    START -> calendario -/

- `clima` y `calendario` corren en paralelo (mismo super-step) y cada uno
  devuelve SOLO su clave del estado, para que el fan-out no choque.
- `rag` espera a ambos (arista de union `["clima", "calendario"] -> rag`).
- Las dependencias (sesion, cliente WeatherAPI, LLM, settings, lugar_id) no
  viven en el estado: viajan en el `context` de la ejecucion (`Dependencias`),
  asi el grafo compilado es unico y reutilizable entre requests.
- Los nodos invocan las tools por su nombre en ESTE modulo (`obtener_clima`,
  `obtener_calendario`, `recuperar_historicos`, `analizar`), de modo que los
  tests pueden sustituirlas con `monkeypatch.setattr(orquestador, "<nombre>", fake)`.

Respaldo estadistico: si el Agente Analista lanza `AnalistaNoDisponibleError`
(429, timeout, sin key), el nodo `analista` arma la prediccion con el promedio,
minimo y maximo de los historicos y marca `fuente_prediccion="estadistica"`.
`AnalistaRespuestaInvalidaError` NO activa el respaldo: se propaga.

No conoce HTTP ni FastAPI.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AnalistaNoDisponibleError, ContextoNoDisponibleError
from app.db.visitas import obtener_lugar_por_codigo
from app.integrations.weather_api import WeatherApiClient
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    ContextoPrediccion,
    DiaGrafico,
    FuentePrediccion,
    HistoricosPrediccion,
    PrediccionLLM,
    PrediccionResponse,
    ResumenHistorico,
)
from app.services.prediccion.agente_analista import analizar
from app.services.prediccion.herramienta_calendario import obtener_calendario
from app.services.prediccion.herramienta_clima import obtener_clima
from app.services.prediccion.rag_historicos import recuperar_historicos

logger = logging.getLogger(__name__)


class EstadoPrediccion(TypedDict, total=False):
    """Estado del grafo. `fecha` es la unica entrada; el resto lo llenan los nodos."""

    fecha: date
    clima: ContextoClima
    calendario: ContextoCalendario
    historicos: ResumenHistorico
    prediccion: PrediccionLLM
    fuente_prediccion: FuentePrediccion


@dataclass(frozen=True)
class Dependencias:
    """Contexto de ejecucion del grafo (no forma parte del estado)."""

    session: AsyncSession
    weather_client: WeatherApiClient
    lugar_id: int
    settings: Settings
    llm: BaseChatModel | None = None


# --- Nodos -------------------------------------------------------------------


async def _nodo_clima(
    state: EstadoPrediccion, runtime: Runtime[Dependencias]
) -> dict[str, ContextoClima]:
    deps = runtime.context
    clima = await obtener_clima(
        state["fecha"],
        deps.session,
        deps.weather_client,
        lugar_id=deps.lugar_id,
        settings=deps.settings,
    )
    return {"clima": clima}


async def _nodo_calendario(state: EstadoPrediccion) -> dict[str, ContextoCalendario]:
    return {"calendario": obtener_calendario(state["fecha"])}


async def _nodo_rag(
    state: EstadoPrediccion, runtime: Runtime[Dependencias]
) -> dict[str, ResumenHistorico]:
    deps = runtime.context
    historicos = await recuperar_historicos(
        deps.session,
        deps.lugar_id,
        state["clima"],
        state["calendario"],
        settings=deps.settings,
    )
    return {"historicos": historicos}


def respaldo_estadistico(historicos: ResumenHistorico) -> PrediccionLLM:
    """Prediccion sin LLM: promedio y rango observados en los dias similares."""
    return PrediccionLLM(
        prediccion_estimada=historicos.promedio,
        rango_minimo=historicos.minimo,
        rango_maximo=historicos.maximo,
        razonamiento_explicado=(
            f"Estimación estadística basada en {historicos.cantidad} días similares "
            "(el análisis con IA no está disponible)."
        ),
    )


async def _nodo_analista(
    state: EstadoPrediccion, runtime: Runtime[Dependencias]
) -> dict[str, PrediccionLLM | FuentePrediccion]:
    deps = runtime.context
    try:
        prediccion = await analizar(
            state["fecha"],
            state["clima"],
            state["calendario"],
            state["historicos"],
            deps.llm,
            settings=deps.settings,
        )
    except AnalistaNoDisponibleError as exc:
        # Solo la fecha y el tipo de error: nunca la key ni el prompt.
        logger.warning(
            "Analista no disponible, se usa respaldo estadistico fecha=%s error=%s",
            state["fecha"].isoformat(),
            type(exc).__name__,
        )
        return {
            "prediccion": respaldo_estadistico(state["historicos"]),
            "fuente_prediccion": "estadistica",
        }
    return {"prediccion": prediccion, "fuente_prediccion": "ia"}


def construir_grafo():
    """Construye y compila el grafo (se usa una vez, al importar el modulo)."""
    grafo = StateGraph(EstadoPrediccion, context_schema=Dependencias)
    grafo.add_node("clima", _nodo_clima)
    grafo.add_node("calendario", _nodo_calendario)
    grafo.add_node("rag", _nodo_rag)
    grafo.add_node("analista", _nodo_analista)

    grafo.add_edge(START, "clima")
    grafo.add_edge(START, "calendario")
    grafo.add_edge(["clima", "calendario"], "rag")
    grafo.add_edge("rag", "analista")
    grafo.add_edge("analista", END)
    return grafo.compile()


GRAFO = construir_grafo()


# --- Caso de uso ---------------------------------------------------------------


class Orquestador:
    """Ejecuta el grafo para una fecha y arma la `PrediccionResponse`.

    `ContextoNoDisponibleError`, `HistoricosNoDisponiblesError` y
    `AnalistaRespuestaInvalidaError` se propagan sin traducir; el router las
    mapea a HTTP. `AnalistaNoDisponibleError` se resuelve con el respaldo
    estadistico dentro del grafo.
    """

    def __init__(
        self,
        session: AsyncSession,
        weather_client: WeatherApiClient,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._weather_client = weather_client
        self._llm = llm
        self._settings = settings or get_settings()

    async def predecir(self, fecha: date) -> PrediccionResponse:
        """Prediccion de visitantes a `PREDICCION_LUGAR_CODIGO` para `fecha`.

        Raises:
            ContextoNoDisponibleError: el lugar no existe o no hay clima posible.
            HistoricosNoDisponiblesError: sin historicos para ese dia de la semana.
            AnalistaRespuestaInvalidaError: el LLM respondio algo invalido (SPEC 06).
        """
        lugar = await obtener_lugar_por_codigo(
            self._session, self._settings.prediccion_lugar_codigo
        )
        if lugar is None:
            raise ContextoNoDisponibleError(
                "No existe el lugar turistico configurado para la prediccion."
            )
        lugar_id, nombre_lugar = lugar

        deps = Dependencias(
            session=self._session,
            weather_client=self._weather_client,
            lugar_id=lugar_id,
            settings=self._settings,
            llm=self._llm,
        )
        estado = await GRAFO.ainvoke({"fecha": fecha}, context=deps)
        logger.info(
            "Prediccion generada fecha=%s fuente=%s",
            fecha.isoformat(),
            estado["fuente_prediccion"],
        )
        return _a_respuesta(fecha, nombre_lugar, estado)


def _a_respuesta(
    fecha: date, lugar: str, estado: EstadoPrediccion
) -> PrediccionResponse:
    clima = estado["clima"]
    calendario = estado["calendario"]
    historicos = estado["historicos"]
    prediccion = estado["prediccion"]
    return PrediccionResponse(
        fecha=fecha,
        lugar=lugar,
        contexto=ContextoPrediccion(
            dia_semana=calendario.dia_semana,
            condicion_clima=clima.condicion_clima,
            temperatura_max=clima.temperatura_max,
            fuente_clima=clima.fuente,
            es_feriado=calendario.es_feriado,
            nombre_feriado=calendario.nombre_feriado,
            temporada=calendario.temporada,
        ),
        historicos=HistoricosPrediccion(
            cantidad=historicos.cantidad,
            promedio=historicos.promedio,
            minimo=historicos.minimo,
            maximo=historicos.maximo,
            nivel_coincidencia=historicos.nivel_coincidencia,
            dias=[
                DiaGrafico(
                    fecha=dia.fecha,
                    visitantes_totales=dia.visitantes_totales,
                    condicion_clima=dia.condicion_clima,
                )
                for dia in sorted(historicos.dias, key=lambda d: d.fecha)
            ],
        ),
        prediccion_estimada=prediccion.prediccion_estimada,
        rango_minimo=prediccion.rango_minimo,
        rango_maximo=prediccion.rango_maximo,
        fuente_prediccion=estado["fuente_prediccion"],
        razonamiento_explicado=prediccion.razonamiento_explicado,
    )

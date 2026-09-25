"""Schemas de la prediccion de visitas (SPEC 04 en adelante).

Incluye:
- Las salidas de las herramientas de contexto (`ContextoClima`, `ContextoCalendario`).
- El subconjunto de WeatherAPI `forecast.json` que consume la Tool Climatica.
- Los dias recuperados y su resumen del RAG de historicos (SPEC 05).
- La salida estructurada del Agente Analista (SPEC 06).

- El request/response del endpoint `POST /api/v1/predicciones` (SPEC 07).
"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Valores validos de `condicion_clima` (SPEC 03), compartidos por los SPEC 04 a 07.
CondicionClima = Literal[
    "Soleado",
    "Parcialmente nublado",
    "Nublado",
    "Lluvia ligera",
    "Lluvia fuerte",
]

FuenteClima = Literal["pronostico", "estimado_historico"]

FuentePrediccion = Literal["ia", "estadistica"]

Temporada = Literal["escolar", "vacacional"]


# --- Salidas de las herramientas de contexto ---------------------------------


class ContextoClima(BaseModel):
    """Salida de la Tool Climatica."""

    fecha: date
    condicion_clima: CondicionClima
    temperatura_max: float
    fuente: FuenteClima


class ContextoCalendario(BaseModel):
    """Salida de la Tool Calendario."""

    fecha: date
    dia_semana: str
    es_feriado: bool
    nombre_feriado: str | None
    temporada: Temporada


# --- RAG de historicos (SPEC 05) --------------------------------------------


class DiaHistorico(BaseModel):
    """Fila de `visitas_historicas` (SPEC 03) sin `id` ni `lugar_id`.

    `condicion_clima` y `temporada` se tipan como `str` (igual que las columnas)
    para no romper la recuperacion ante un valor fuera de catalogo en la tabla.
    """

    fecha: date
    dia_semana: str
    condicion_clima: str
    temperatura_max: float
    es_feriado: bool
    temporada: str
    visitantes_totales: int


class ResumenHistorico(BaseModel):
    """Conocimiento recuperado de los historicos que recibe el LLM (SPEC 06)."""

    nivel_coincidencia: int = Field(ge=1, le=4)
    criterios: list[str]
    cantidad: int = Field(ge=1)
    promedio: int
    minimo: int
    maximo: int
    resumen_texto: str
    dias: list[DiaHistorico]


# --- Agente Analista (SPEC 06) ----------------------------------------------


class PrediccionLLM(BaseModel):
    """Salida estructurada del LLM.

    Exige `0 <= rango_minimo <= prediccion_estimada <= rango_maximo`.
    """

    prediccion_estimada: int = Field(ge=0)
    rango_minimo: int = Field(ge=0)
    rango_maximo: int = Field(ge=0)
    razonamiento_explicado: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def _validar_rango(self) -> Self:
        if not (self.rango_minimo <= self.prediccion_estimada <= self.rango_maximo):
            raise ValueError(
                "Se requiere rango_minimo <= prediccion_estimada <= rango_maximo."
            )
        return self


# --- Endpoint de prediccion (SPEC 07) --------------------------------------


class PrediccionRequest(BaseModel):
    """Body de `POST /api/v1/predicciones`. `fecha` en ISO `YYYY-MM-DD`."""

    fecha: date


class ContextoPrediccion(BaseModel):
    """Contexto de clima + calendario usado para predecir."""

    dia_semana: str
    condicion_clima: CondicionClima
    temperatura_max: float
    fuente_clima: FuenteClima
    es_feriado: bool
    nombre_feriado: str | None
    temporada: Temporada


class DiaGrafico(BaseModel):
    """Dia similar expuesto para el grafico del Planificador (SPEC 07/08)."""

    fecha: date
    visitantes_totales: int
    condicion_clima: str


class HistoricosPrediccion(BaseModel):
    """Resumen publico de los historicos recuperados.

    `dias` va ordenado por `fecha` ASC y solo expone los 3 campos de `DiaGrafico`.
    """

    cantidad: int
    promedio: int
    minimo: int
    maximo: int
    nivel_coincidencia: int
    dias: list[DiaGrafico]


class PrediccionResponse(BaseModel):
    """Respuesta 200 de `POST /api/v1/predicciones` (Contrato del SPEC 07 §5)."""

    fecha: date
    lugar: str
    contexto: ContextoPrediccion
    historicos: HistoricosPrediccion
    prediccion_estimada: int
    rango_minimo: int
    rango_maximo: int
    fuente_prediccion: FuentePrediccion
    razonamiento_explicado: str


# --- WeatherAPI forecast.json (solo los campos consumidos) --------------------


class WeatherApiForecastCondition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: int
    text: str = ""


class WeatherApiForecastDayData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    maxtemp_c: float
    condition: WeatherApiForecastCondition


class WeatherApiForecastDay(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    day: WeatherApiForecastDayData


class WeatherApiForecast(BaseModel):
    model_config = ConfigDict(extra="ignore")

    forecastday: list[WeatherApiForecastDay] = Field(default_factory=list)


class WeatherApiForecastResponse(BaseModel):
    """Subconjunto de forecast.json que consume la aplicacion."""

    model_config = ConfigDict(extra="ignore")

    forecast: WeatherApiForecast

"""RAG de historicos (SPEC 05): dias pasados parecidos a la fecha pedida.

Relaja los filtros por niveles y se detiene en el primero que alcance
`RAG_MIN_RESULTADOS` filas:

| Nivel | Filtros (AND)                                               |
|-------|-------------------------------------------------------------|
| 1     | dia_semana + condicion_clima + es_feriado + temporada       |
| 2     | dia_semana + condicion_clima + es_feriado                   |
| 3     | dia_semana + condicion_clima                                |
| 4     | dia_semana                                                  |

Si ningun nivel llega al minimo se usa el nivel 4 con las filas que haya; con
0 filas en el nivel 4 se lanza `HistoricosNoDisponiblesError`.

No conoce HTTP ni FastAPI.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import HistoricosNoDisponiblesError
from app.db.visitas import buscar_dias_similares
from app.models.prediccion import (
    ContextoCalendario,
    ContextoClima,
    DiaHistorico,
    ResumenHistorico,
)

# Filtros opcionales de cada nivel (`dia_semana` se aplica siempre).
_FILTROS_POR_NIVEL: dict[int, tuple[str, ...]] = {
    1: ("condicion_clima", "es_feriado", "temporada"),
    2: ("condicion_clima", "es_feriado"),
    3: ("condicion_clima",),
    4: (),
}

# Plural en minusculas de cada dia (los terminados en "s" no cambian).
_DIA_PLURAL: dict[str, str] = {
    "Lunes": "lunes",
    "Martes": "martes",
    "Miércoles": "miércoles",
    "Jueves": "jueves",
    "Viernes": "viernes",
    "Sábado": "sábados",
    "Domingo": "domingos",
}

_PLANTILLA_RESUMEN = (
    "En los últimos {n} {criterios}, el promedio de visitas fue de {promedio} "
    "personas, con un mínimo de {minimo} y un pico de {maximo}."
)


async def recuperar_historicos(
    session: AsyncSession,
    lugar_id: int,
    clima: ContextoClima,
    calendario: ContextoCalendario,
    *,
    settings: Settings | None = None,
) -> ResumenHistorico:
    """Resume los dias historicos de `lugar_id` mas parecidos a la fecha pedida.

    Firma del SPEC 05 ampliada con `settings` keyword-only (inyectable en tests;
    por defecto `get_settings()`). La fecha consultada (`calendario.fecha`)
    nunca se incluye.

    Raises:
        HistoricosNoDisponiblesError: si no hay ningun dia historico del lugar
            para ese dia de la semana (0 filas en el nivel 4).
    """
    cfg = settings or get_settings()
    valores: dict[str, Any] = {
        "condicion_clima": clima.condicion_clima,
        "es_feriado": calendario.es_feriado,
        "temporada": calendario.temporada,
    }

    nivel = 1
    dias: list[DiaHistorico] = []
    for nivel, filtros in _FILTROS_POR_NIVEL.items():
        dias = await buscar_dias_similares(
            session,
            lugar_id=lugar_id,
            fecha_excluida=calendario.fecha,
            dia_semana=calendario.dia_semana,
            temperatura=clima.temperatura_max,
            limite=cfg.rag_max_resultados,
            **{nombre: valores[nombre] for nombre in filtros},
        )
        if len(dias) >= cfg.rag_min_resultados:
            break
    # Al terminar el loop sin `break`, `nivel` = 4 y `dias` son las filas del nivel 4.

    if not dias:
        raise HistoricosNoDisponiblesError(
            f"No hay visitas historicas para los dias {calendario.dia_semana}."
        )

    filtros_usados = _FILTROS_POR_NIVEL[nivel]
    visitantes = [dia.visitantes_totales for dia in dias]
    promedio = _media_redondeada(visitantes)
    minimo, maximo = min(visitantes), max(visitantes)
    criterios_texto = describir_criterios(
        calendario.dia_semana, filtros_usados, valores
    )

    return ResumenHistorico(
        nivel_coincidencia=nivel,
        criterios=["dia_semana", *filtros_usados],
        cantidad=len(dias),
        promedio=promedio,
        minimo=minimo,
        maximo=maximo,
        resumen_texto=_PLANTILLA_RESUMEN.format(
            n=len(dias),
            criterios=criterios_texto,
            promedio=promedio,
            minimo=minimo,
            maximo=maximo,
        ),
        dias=dias,
    )


def describir_criterios(
    dia_semana: str, filtros: tuple[str, ...], valores: dict[str, Any]
) -> str:
    """Texto en español de los criterios aplicados (determinista).

    - Base: el dia en plural y minusculas ("Domingo" -> "domingos"; los dias
      terminados en "s" no cambian; un valor desconocido se pasa a minusculas).
    - `condicion_clima`: " con clima {condicion}" (condicion tal cual).
    - `es_feriado`: ", feriados" solo si el filtro es `True`.
    - `temporada`: " en temporada vacacional" solo si es "vacacional".

    Los filtros "normales" (no feriado, temporada escolar) no se verbalizan,
    por eso el nivel 1 de un domingo soleado escolar da "domingos con clima Soleado".
    Ejemplo completo: "domingos con clima Soleado, feriados en temporada vacacional".
    """
    texto = _DIA_PLURAL.get(dia_semana, dia_semana.lower())
    if "condicion_clima" in filtros:
        texto += f" con clima {valores['condicion_clima']}"
    if "es_feriado" in filtros and valores["es_feriado"] is True:
        texto += ", feriados"
    if "temporada" in filtros and valores["temporada"] == "vacacional":
        texto += " en temporada vacacional"
    return texto


def _media_redondeada(valores: list[int]) -> int:
    """Media aritmetica redondeada a entero (half-up, sin error de coma flotante)."""
    media = Decimal(sum(valores)) / Decimal(len(valores))
    return int(media.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

"""Tool Calendario (SPEC 04): dia de la semana, feriado/fiesta local y temporada.

Funcion pura: sin red ni BD. Reutiliza `app/data/calendario_peru.py` (SPEC 03)
sin duplicar las listas de feriados.
"""

from datetime import date

from app.data.calendario_peru import (
    dia_semana_es,
    feriado_nacional,
    fiesta_local,
    temporada,
)
from app.models.prediccion import ContextoCalendario


def obtener_calendario(fecha: date) -> ContextoCalendario:
    """Contexto de calendario de `fecha`.

    `nombre_feriado` prioriza la fiesta local (Huanuco) sobre el feriado
    nacional si coincidieran; `es_feriado` es True si hay cualquiera de los dos.
    """
    nombre = fiesta_local(fecha) or feriado_nacional(fecha)
    return ContextoCalendario(
        fecha=fecha,
        dia_semana=dia_semana_es(fecha),
        es_feriado=nombre is not None,
        nombre_feriado=nombre,
        temporada=temporada(fecha),
    )

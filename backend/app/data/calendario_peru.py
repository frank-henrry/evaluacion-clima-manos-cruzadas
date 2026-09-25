"""Calendario peruano: feriados nacionales, fiestas locales de Huanuco y temporadas.

Modulo puro, sin dependencias externas ni acceso a BD. Lo usan el generador de
visitas historicas (SPEC 03) y la prediccion (SPEC 04).
"""

from datetime import date, timedelta
from typing import Literal

# Feriados nacionales de fecha fija, indexados por (mes, dia).
_FERIADOS_FIJOS: dict[tuple[int, int], str] = {
    (1, 1): "Año Nuevo",
    (5, 1): "Día del Trabajo",
    (6, 7): "Batalla de Arica y Día de la Bandera",
    (6, 29): "San Pedro y San Pablo",
    (7, 23): "Día de la Fuerza Aérea del Perú",
    (7, 28): "Fiestas Patrias",
    (7, 29): "Fiestas Patrias",
    (8, 6): "Batalla de Junín",
    (8, 30): "Santa Rosa de Lima",
    (10, 8): "Combate de Angamos",
    (11, 1): "Día de Todos los Santos",
    (12, 8): "Inmaculada Concepción",
    (12, 9): "Batalla de Ayacucho",
    (12, 25): "Navidad",
}

# Fiestas locales de Huanuco.
_FIESTAS_LOCALES: dict[tuple[int, int], str] = {
    (6, 24): "Fiesta de San Juan",
    (8, 15): "Aniversario de Huánuco",
}

# Rangos (inclusive) de temporada vacacional, como ((mes, dia), (mes, dia)).
_RANGOS_VACACIONALES: tuple[tuple[tuple[int, int], tuple[int, int]], ...] = (
    ((1, 1), (3, 15)),
    ((7, 22), (8, 10)),
    ((12, 20), (12, 31)),
)

_DIAS_SEMANA: tuple[str, ...] = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)


def _domingo_de_pascua(anio: int) -> date:
    """Domingo de Pascua segun el algoritmo gregoriano (Meeus/Jones/Butcher)."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def feriado_nacional(fecha: date) -> str | None:
    """Nombre del feriado nacional de `fecha`, o None si no lo es."""
    fijo = _FERIADOS_FIJOS.get((fecha.month, fecha.day))
    if fijo is not None:
        return fijo

    pascua = _domingo_de_pascua(fecha.year)
    if fecha == pascua - timedelta(days=3):
        return "Jueves Santo"
    if fecha == pascua - timedelta(days=2):
        return "Viernes Santo"
    return None


def fiesta_local(fecha: date) -> str | None:
    """Nombre de la fiesta local de Huanuco en `fecha`, o None si no la hay."""
    return _FIESTAS_LOCALES.get((fecha.month, fecha.day))


def temporada(fecha: date) -> Literal["escolar", "vacacional"]:
    """`vacacional` dentro de los rangos de vacaciones; `escolar` el resto del año."""
    clave = (fecha.month, fecha.day)
    for inicio, fin in _RANGOS_VACACIONALES:
        if inicio <= clave <= fin:
            return "vacacional"
    return "escolar"


def dia_semana_es(fecha: date) -> str:
    """Dia de la semana en español: Lunes..Domingo."""
    return _DIAS_SEMANA[fecha.weekday()]

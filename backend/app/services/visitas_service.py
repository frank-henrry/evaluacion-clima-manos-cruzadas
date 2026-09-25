"""Consulta del historico de visitas con filtros, orden y paginacion (SPEC 09).

- Valida la combinacion de filtros (regla de dominio, no de HTTP).
- Traduce `fecha` / `anio` / `anio + mes` a un rango semiabierto `[desde, hasta)`.
- Resuelve el lugar por `settings.prediccion_lugar_codigo`.
- Las queries se invocan por su nombre en ESTE modulo (`obtener_lugar_por_codigo`,
  `listar_visitas`, `resumir_visitas`), asi los tests pueden sustituirlas con
  `monkeypatch.setattr(visitas_service, "<nombre>", fake)`.

No conoce HTTP ni FastAPI.
"""

import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import FiltrosInvalidosError, HistoricoNoDisponibleError
from app.db.visitas import listar_visitas, obtener_lugar_por_codigo, resumir_visitas
from app.models.visitas import (
    DireccionOrden,
    EstadisticasVisitas,
    FiltrosVisitas,
    OrdenVisitas,
    ResumenVisitas,
    VisitasResponse,
)

MENSAJE_FECHA_Y_PERIODO = "Usá fecha, o año (con mes opcional), no ambos."
MENSAJE_MES_SIN_ANIO = "El mes requiere un año."


def validar_filtros(fecha: date | None, anio: int | None, mes: int | None) -> None:
    """Lanza `FiltrosInvalidosError` si la combinacion no es uno de los modos validos."""
    if fecha is not None and (anio is not None or mes is not None):
        raise FiltrosInvalidosError(MENSAJE_FECHA_Y_PERIODO)
    if mes is not None and anio is None:
        raise FiltrosInvalidosError(MENSAJE_MES_SIN_ANIO)


def rango_de_fechas(
    fecha: date | None, anio: int | None, mes: int | None
) -> tuple[date | None, date | None]:
    """`(desde, hasta)` semiabierto para el filtro ya validado; `(None, None)` = todo."""
    if fecha is not None:
        return fecha, fecha + timedelta(days=1)
    if anio is not None and mes is not None:
        siguiente = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
        return date(anio, mes, 1), siguiente
    if anio is not None:
        return date(anio, 1, 1), date(anio + 1, 1, 1)
    return None, None


def armar_resumen(estadisticas: EstadisticasVisitas) -> ResumenVisitas | None:
    """Resumen con promedio entero half-up, o `None` si el periodo no tiene filas."""
    if (
        estadisticas.total == 0
        or estadisticas.total_visitantes is None
        or estadisticas.minimo is None
        or estadisticas.maximo is None
    ):
        return None
    promedio = (
        Decimal(estadisticas.total_visitantes) / Decimal(estadisticas.total)
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return ResumenVisitas(
        promedio=int(promedio),
        minimo=estadisticas.minimo,
        maximo=estadisticas.maximo,
        total_visitantes=estadisticas.total_visitantes,
    )


class VisitasService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    async def listar(
        self,
        *,
        fecha: date | None = None,
        anio: int | None = None,
        mes: int | None = None,
        orden: OrdenVisitas = "fecha",
        direccion: DireccionOrden = "desc",
        pagina: int = 1,
        tamano: int = 31,
    ) -> VisitasResponse:
        """Pagina del historico del lugar configurado.

        Lanza `FiltrosInvalidosError` ante una combinacion invalida (antes de
        tocar la base) y `HistoricoNoDisponibleError` si el lugar no existe.
        """
        validar_filtros(fecha, anio, mes)
        desde, hasta = rango_de_fechas(fecha, anio, mes)

        lugar = await obtener_lugar_por_codigo(
            self._session, self._settings.prediccion_lugar_codigo
        )
        if lugar is None:
            raise HistoricoNoDisponibleError()
        lugar_id, nombre = lugar

        estadisticas = await resumir_visitas(
            self._session, lugar_id=lugar_id, desde=desde, hasta=hasta
        )
        total = estadisticas.total
        total_paginas = math.ceil(total / tamano) if total else 0

        items = []
        if pagina <= total_paginas:
            items = await listar_visitas(
                self._session,
                lugar_id=lugar_id,
                desde=desde,
                hasta=hasta,
                orden=orden,
                direccion=direccion,
                limite=tamano,
                offset=(pagina - 1) * tamano,
            )

        return VisitasResponse(
            lugar=nombre,
            filtros=FiltrosVisitas(fecha=fecha, anio=anio, mes=mes),
            orden=orden,
            direccion=direccion,
            pagina=pagina,
            tamano=tamano,
            total=total,
            total_paginas=total_paginas,
            resumen=armar_resumen(estadisticas),
            items=items,
        )

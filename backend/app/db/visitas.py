"""Acceso a datos de `lugar_turistico` y `visitas_historicas`. Queries via SQLAlchemy (parametrizadas)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LugarTuristico, VisitaHistorica
from app.models.prediccion import DiaHistorico
from app.models.visitas import (
    DireccionOrden,
    EstadisticasVisitas,
    OrdenVisitas,
    VisitaItem,
)

_UN_DECIMAL = Decimal("0.1")

# Lista blanca de columnas de orden del historico (SPEC 09): nunca se interpola.
_COLUMNAS_ORDEN = {
    "fecha": VisitaHistorica.fecha,
    "visitantes": VisitaHistorica.visitantes_totales,
}


async def obtener_lugar_por_codigo(
    session: AsyncSession, codigo: str
) -> tuple[int, str] | None:
    """`(id, nombre)` del lugar turistico con `codigo`, o `None` si no existe."""
    stmt = select(LugarTuristico.id, LugarTuristico.nombre).where(
        LugarTuristico.codigo == codigo
    )
    fila = (await session.execute(stmt)).first()
    if fila is None:
        return None
    lugar_id, nombre = fila
    return int(lugar_id), nombre


async def clima_tipico_del_mes(
    session: AsyncSession, lugar_id: int, mes: int
) -> tuple[str, float] | None:
    """Condicion mas frecuente del `mes` para `lugar_id` y su temperatura maxima promedio.

    Devuelve `(condicion_clima, temperatura_promedio)` con la temperatura
    redondeada a 1 decimal (half-up), o `None` si no hay historicos ese mes.
    El promedio se calcula sobre los dias de esa condicion. En empate de
    frecuencia gana la condicion con menor nombre alfabetico (determinista).
    """
    conteo = func.count(VisitaHistorica.id).label("conteo")
    stmt = (
        select(
            VisitaHistorica.condicion_clima,
            conteo,
            func.avg(VisitaHistorica.temperatura_max).label("temperatura_promedio"),
        )
        .where(
            VisitaHistorica.lugar_id == lugar_id,
            extract("month", VisitaHistorica.fecha) == mes,
        )
        .group_by(VisitaHistorica.condicion_clima)
        .order_by(conteo.desc(), VisitaHistorica.condicion_clima.asc())
        .limit(1)
    )
    fila = (await session.execute(stmt)).first()
    if fila is None:
        return None

    condicion, _, promedio = fila
    temperatura = Decimal(str(promedio)).quantize(_UN_DECIMAL, rounding=ROUND_HALF_UP)
    return condicion, float(temperatura)


async def buscar_dias_similares(
    session: AsyncSession,
    *,
    lugar_id: int,
    fecha_excluida: date,
    dia_semana: str,
    temperatura: float,
    condicion_clima: str | None = None,
    es_feriado: bool | None = None,
    temporada: str | None = None,
    limite: int = 10,
) -> list[DiaHistorico]:
    """Dias historicos de `lugar_id` parecidos a la fecha consultada (SPEC 05).

    Siempre filtra por `lugar_id` y `dia_semana` y excluye `fecha_excluida`.
    `condicion_clima`, `es_feriado` y `temporada` solo se aplican si no son
    `None`. Orden: temperatura maxima mas cercana a `temperatura` y, en empate,
    la fecha mas reciente. Devuelve como maximo `limite` filas.
    """
    filtros = [
        VisitaHistorica.lugar_id == lugar_id,
        VisitaHistorica.fecha != fecha_excluida,
        VisitaHistorica.dia_semana == dia_semana,
    ]
    if condicion_clima is not None:
        filtros.append(VisitaHistorica.condicion_clima == condicion_clima)
    if es_feriado is not None:
        filtros.append(VisitaHistorica.es_feriado == es_feriado)
    if temporada is not None:
        filtros.append(VisitaHistorica.temporada == temporada)

    stmt = (
        select(
            VisitaHistorica.fecha,
            VisitaHistorica.dia_semana,
            VisitaHistorica.condicion_clima,
            VisitaHistorica.temperatura_max,
            VisitaHistorica.es_feriado,
            VisitaHistorica.temporada,
            VisitaHistorica.visitantes_totales,
        )
        .where(*filtros)
        .order_by(
            # Decimal para comparar NUMERIC con NUMERIC (sin error de coma flotante).
            func.abs(
                VisitaHistorica.temperatura_max - Decimal(str(temperatura))
            ).asc(),
            VisitaHistorica.fecha.desc(),
        )
        .limit(limite)
    )
    filas = (await session.execute(stmt)).all()
    return [DiaHistorico.model_validate(dict(fila._mapping)) for fila in filas]


def _filtros_periodo(
    lugar_id: int, desde: date | None, hasta: date | None
) -> list:
    """Filtro por lugar y rango semiabierto `[desde, hasta)` (usa el indice por fecha)."""
    filtros = [VisitaHistorica.lugar_id == lugar_id]
    if desde is not None:
        filtros.append(VisitaHistorica.fecha >= desde)
    if hasta is not None:
        filtros.append(VisitaHistorica.fecha < hasta)
    return filtros


async def listar_visitas(
    session: AsyncSession,
    *,
    lugar_id: int,
    desde: date | None,
    hasta: date | None,
    orden: OrdenVisitas,
    direccion: DireccionOrden,
    limite: int,
    offset: int,
) -> list[VisitaItem]:
    """Pagina de visitas de `lugar_id` con `desde <= fecha < hasta` (SPEC 09).

    `desde`/`hasta` en `None` no acotan ese extremo. `orden` se resuelve contra
    la lista blanca `_COLUMNAS_ORDEN`; el desempate estable es `fecha DESC`.
    """
    columna = _COLUMNAS_ORDEN[orden]
    criterios = [columna.asc() if direccion == "asc" else columna.desc()]
    if orden != "fecha":
        criterios.append(VisitaHistorica.fecha.desc())

    stmt = (
        select(
            VisitaHistorica.fecha,
            VisitaHistorica.dia_semana,
            VisitaHistorica.condicion_clima,
            VisitaHistorica.temperatura_max,
            VisitaHistorica.es_feriado,
            VisitaHistorica.temporada,
            VisitaHistorica.visitantes_totales,
        )
        .where(*_filtros_periodo(lugar_id, desde, hasta))
        .order_by(*criterios)
        .limit(limite)
        .offset(offset)
    )
    filas = (await session.execute(stmt)).all()
    return [VisitaItem.model_validate(dict(fila._mapping)) for fila in filas]


async def resumir_visitas(
    session: AsyncSession,
    *,
    lugar_id: int,
    desde: date | None,
    hasta: date | None,
) -> EstadisticasVisitas:
    """`COUNT`, `SUM`, `MIN` y `MAX` de visitantes sobre TODO el periodo filtrado."""
    stmt = select(
        func.count(VisitaHistorica.id),
        func.sum(VisitaHistorica.visitantes_totales),
        func.min(VisitaHistorica.visitantes_totales),
        func.max(VisitaHistorica.visitantes_totales),
    ).where(*_filtros_periodo(lugar_id, desde, hasta))
    total, suma, minimo, maximo = (await session.execute(stmt)).one()
    return EstadisticasVisitas(
        total=int(total or 0),
        total_visitantes=None if suma is None else int(suma),
        minimo=None if minimo is None else int(minimo),
        maximo=None if maximo is None else int(maximo),
    )

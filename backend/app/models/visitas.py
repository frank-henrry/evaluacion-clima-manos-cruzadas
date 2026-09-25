"""Schemas del historico de visitas (SPEC 09): `GET /api/v1/visitas`."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

OrdenVisitas = Literal["fecha", "visitantes"]

DireccionOrden = Literal["asc", "desc"]


class VisitaItem(BaseModel):
    """Fila de `visitas_historicas` expuesta en la tabla (sin `id` ni `lugar_id`).

    `condicion_clima` y `temporada` se tipan como `str` (igual que las columnas)
    para no romper la consulta ante un valor fuera de catalogo en la tabla.
    """

    fecha: date
    dia_semana: str
    condicion_clima: str
    temperatura_max: float
    es_feriado: bool
    temporada: str
    visitantes_totales: int


class EstadisticasVisitas(BaseModel):
    """Agregados crudos de la query de resumen (capa db -> service).

    Con `total == 0` los agregados son `None`.
    """

    total: int
    total_visitantes: int | None
    minimo: int | None
    maximo: int | None


class ResumenVisitas(BaseModel):
    """Resumen del periodo filtrado (todas las filas del filtro, no solo la pagina)."""

    promedio: int
    minimo: int
    maximo: int
    total_visitantes: int


class FiltrosVisitas(BaseModel):
    """Filtros aplicados, tal como llegaron (los ausentes van en `null`)."""

    fecha: date | None
    anio: int | None
    mes: int | None


class VisitasResponse(BaseModel):
    """Respuesta 200 de `GET /api/v1/visitas` (Contrato del SPEC 09 §5)."""

    lugar: str
    filtros: FiltrosVisitas
    orden: OrdenVisitas
    direccion: DireccionOrden
    pagina: int
    tamano: int
    total: int
    total_paginas: int
    resumen: ResumenVisitas | None
    items: list[VisitaItem]

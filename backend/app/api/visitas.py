"""Endpoint protegido para consultar el historico de visitas (SPEC 09)."""

import logging
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_visitas_service, require_authenticated_user
from app.core.exceptions import FiltrosInvalidosError, HistoricoNoDisponibleError
from app.models.visitas import VisitasResponse
from app.services.visitas_service import VisitasService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["visitas"])


@router.get(
    "/visitas",
    response_model=VisitasResponse,
    responses={
        401: {"description": "JWT ausente, invalido o expirado."},
        422: {"description": "Combinacion de filtros, tipo o rango invalido."},
        503: {"description": "Historico no disponible (lugar inexistente)."},
    },
)
async def listar_visitas(
    _authenticated_user: Annotated[str, Depends(require_authenticated_user)],
    service: Annotated[VisitasService, Depends(get_visitas_service)],
    fecha: Annotated[date | None, Query(description="Dia exacto YYYY-MM-DD")] = None,
    anio: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    orden: Literal["fecha", "visitantes"] = "fecha",
    direccion: Literal["asc", "desc"] = "desc",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 31,
) -> VisitasResponse:
    try:
        return await service.listar(
            fecha=fecha,
            anio=anio,
            mes=mes,
            orden=orden,
            direccion=direccion,
            pagina=pagina,
            tamano=tamano,
        )
    except FiltrosInvalidosError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc
    except HistoricoNoDisponibleError as exc:
        logger.warning("Historico no disponible error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Histórico no disponible.",
        ) from exc

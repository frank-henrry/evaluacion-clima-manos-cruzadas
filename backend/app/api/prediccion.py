"""Endpoint protegido para predecir los visitantes de una fecha (SPEC 07)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_orquestador, require_authenticated_user
from app.core.exceptions import (
    AnalistaNoDisponibleError,
    AnalistaRespuestaInvalidaError,
    ContextoNoDisponibleError,
    HistoricosNoDisponiblesError,
)
from app.models.prediccion import PrediccionRequest, PrediccionResponse
from app.services.prediccion.orquestador import Orquestador

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["prediccion"])


@router.post(
    "/predicciones",
    response_model=PrediccionResponse,
    responses={
        401: {"description": "JWT ausente, invalido o expirado."},
        422: {"description": "Fecha invalida (se espera ISO YYYY-MM-DD)."},
        502: {"description": "El analista devolvio una respuesta invalida."},
        503: {"description": "Servicio de prediccion no disponible."},
    },
)
async def predecir(
    _authenticated_user: Annotated[str, Depends(require_authenticated_user)],
    body: PrediccionRequest,
    orquestador: Annotated[Orquestador, Depends(get_orquestador)],
) -> PrediccionResponse:
    try:
        return await orquestador.predecir(body.fecha)
    except AnalistaRespuestaInvalidaError as exc:
        _log_error(exc, body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El analista devolvió una respuesta inválida.",
        ) from exc
    except (
        ContextoNoDisponibleError,
        HistoricosNoDisponiblesError,
        AnalistaNoDisponibleError,
    ) as exc:
        _log_error(exc, body)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de predicción no disponible.",
        ) from exc


def _log_error(exc: Exception, body: PrediccionRequest) -> None:
    """Solo la clase del error y la fecha: nunca la key ni el prompt."""
    logger.warning(
        "Prediccion fallida fecha=%s error=%s",
        body.fecha.isoformat(),
        type(exc).__name__,
    )

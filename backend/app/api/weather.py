"""Endpoint protegido para consultar el clima actual de una ciudad."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_weather_service,
    require_authenticated_user,
    validated_location,
)
from app.core.exceptions import (
    LocationNotFoundError,
    WeatherProviderResponseError,
    WeatherProviderUnavailableError,
)
from app.models.weather import WeatherResponse
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/api/v1", tags=["weather"])


@router.get(
    "/weather",
    response_model=WeatherResponse,
    responses={
        401: {"description": "JWT ausente, invalido o expirado."},
        404: {"description": "Ciudad no encontrada."},
        422: {"description": "Parametro location invalido."},
        502: {"description": "Respuesta invalida del proveedor."},
        503: {"description": "Proveedor meteorologico no disponible."},
    },
)
async def weather(
    _authenticated_user: Annotated[str, Depends(require_authenticated_user)],
    location: Annotated[str, Depends(validated_location)],
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> WeatherResponse:
    try:
        return await service.get_weather(location)
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la ciudad.",
        ) from exc
    except WeatherProviderResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El proveedor devolvió una respuesta inválida.",
        ) from exc
    except WeatherProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio meteorológico no disponible.",
        ) from exc

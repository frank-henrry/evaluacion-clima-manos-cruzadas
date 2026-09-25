"""Dependencias HTTP compartidas por los routers."""

import unicodedata
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.integrations.weather_api import WeatherApiClient
from app.services.prediccion.orquestador import Orquestador
from app.services.visitas_service import VisitasService
from app.services.weather_service import WeatherService

_bearer_scheme = HTTPBearer(auto_error=False)


async def require_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise unauthorized from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise unauthorized
    return subject


async def validated_location(
    location: Annotated[str, Query(description="Nombre de la ciudad")],
) -> str:
    normalized = location.strip()
    contains_control = any(unicodedata.category(char) == "Cc" for char in normalized)
    if not 1 <= len(normalized) <= 100 or contains_control:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La ubicación debe contener entre 1 y 100 caracteres y no incluir controles.",
        )
    return normalized


async def get_weather_service() -> WeatherService:
    return WeatherService(WeatherApiClient(get_settings()))


async def get_orquestador(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Orquestador:
    settings = get_settings()
    return Orquestador(session, WeatherApiClient(settings), settings=settings)


async def get_visitas_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VisitasService:
    return VisitasService(session, settings=get_settings())

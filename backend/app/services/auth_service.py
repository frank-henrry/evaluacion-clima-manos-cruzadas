"""Logica de autenticacion. No conoce HTTP (ni Request/Response de FastAPI)."""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import create_access_token, verify_password
from app.db.users import get_user_by_correo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthResult:
    correo: str
    token: str


async def authenticate(session: AsyncSession, correo: str, password: str) -> AuthResult:
    """Valida credenciales y devuelve el correo + un JWT recien emitido.

    Lanza AuthError (mensaje generico) si el correo no esta registrado o si la
    contrasena no coincide. No se distingue un caso del otro.
    """
    correo_norm = correo.strip().lower()

    user = await get_user_by_correo(session, correo_norm)
    if user is None:
        logger.info("Login rechazado para correo=%s (no registrado)", correo_norm)
        raise AuthError()

    if not verify_password(password, user.password_hash):
        logger.info("Login rechazado para correo=%s (contrasena incorrecta)", correo_norm)
        raise AuthError()

    logger.info("Login OK para correo=%s", user.correo)
    return AuthResult(correo=user.correo, token=create_access_token(user.correo))

"""Primitivas de seguridad: hashing de contrasenas (bcrypt) y emision de JWT.

Este modulo no importa nada de FastAPI ni conoce HTTP.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Compara una contrasena en claro contra su hash bcrypt (tiempo constante)."""
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except ValueError:
        # Hash con formato invalido almacenado en la db.
        return False


def create_access_token(correo: str) -> str:
    """Emite un JWT HS256 firmado con `JWT_SECRET`.

    Claims: `sub` y `correo` = correo del usuario, `iat`, `exp`.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": correo,
        "correo": correo,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verifica firma y expiracion de un JWT. Lanza jose.JWTError si es invalido."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

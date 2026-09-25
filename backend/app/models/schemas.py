"""Schemas Pydantic de request/response del endpoint de login."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

_WHITESPACE_RE = re.compile(r"\s")


class LoginRequest(BaseModel):
    """Body de POST /auth/login. Ambos campos son obligatorios."""

    correo: EmailStr
    password: str = Field(min_length=1)

    @field_validator("correo", mode="before")
    @classmethod
    def correo_sin_espacios(cls, value: object) -> object:
        if isinstance(value, str) and _WHITESPACE_RE.search(value):
            raise ValueError("El correo no debe contener espacios en blanco.")
        return value

    @field_validator("password")
    @classmethod
    def password_no_vacio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La contraseña es obligatoria.")
        return value


class LoginResponse(BaseModel):
    """Respuesta OK. `token` es un JWT HS256."""

    correo: EmailStr
    token: str
    token_type: str = "bearer"

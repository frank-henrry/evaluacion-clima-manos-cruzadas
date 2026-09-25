"""Siembra idempotente de usuarios de prueba.

Alternativa a db/init.sql para entornos ya inicializados (p. ej. correr uvicorn
local contra un Postgres que ya tiene el volumen creado). Ejecutar:

    python seed.py

Requiere las mismas env vars que la app (DATABASE_URL, JWT_SECRET, ...).
Las credenciales corresponden a los usuarios de prueba documentados en el README.
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Base, User
from app.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")

SEED_USERS: list[tuple[str, str]] = [
    ("admin@practica.com", "admin123"),
    ("jperez@practica.com", "Practica-1"),
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        for correo, password in SEED_USERS:
            correo_norm = correo.strip().lower()
            existing = (
                await session.execute(select(User).where(User.correo == correo_norm))
            ).scalar_one_or_none()

            if existing is not None:
                logger.info("= %s ya existe, se omite", correo_norm)
                continue

            session.add(
                User(correo=correo_norm, password_hash=hash_password(password))
            )
            logger.info("+ %s insertado", correo_norm)

        await session.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

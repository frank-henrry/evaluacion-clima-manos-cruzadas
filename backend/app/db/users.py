"""Acceso a datos de `users`. Queries via SQLAlchemy (parametrizadas)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_correo(session: AsyncSession, correo: str) -> User | None:
    result = await session.execute(select(User).where(User.correo == correo))
    return result.scalar_one_or_none()

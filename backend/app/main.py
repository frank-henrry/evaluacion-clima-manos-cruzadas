"""Punto de entrada de la API de autenticacion (FastAPI)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, weather
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Crea la tabla `users` si no existe. En Docker el esquema real lo siembra
    # db/init.sql; esto solo suaviza el arranque local sin ese script.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("CORS habilitado para: %s", settings.cors_origins_list)
    yield
    await engine.dispose()


app = FastAPI(title="Practica 1 - Auth API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(weather.router)

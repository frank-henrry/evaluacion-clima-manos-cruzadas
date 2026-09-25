"""Siembra idempotente del lugar "Las Manos Cruzadas" y sus visitas historicas.

Genera 2 años de visitas diarias inventadas (2024-01-01 a 2025-12-31) con
patrones coherentes (fin de semana, feriados, clima, temporada) y las inserta
en PostgreSQL. Ejecutar:

    python seed_visitas.py                              # local (con .env)
    docker compose exec backend python seed_visitas.py  # Docker

Requiere las mismas env vars que la app (DATABASE_URL, JWT_SECRET, ...).
Ejecutarlo varias veces no duplica ni el lugar ni las visitas.

`generar_visitas()` es pura (sin BD): los modulos de BD se importan dentro de
`main()` para que el generador pueda importarse y testearse sin Postgres ni
variables de entorno.
"""

import asyncio
import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from app.data.calendario_peru import (
    dia_semana_es,
    feriado_nacional,
    fiesta_local,
    temporada,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_visitas")

LUGAR: dict[str, str | int] = {
    "codigo": "manos-cruzadas",
    "nombre": "Las Manos Cruzadas",
    "sitio": "Templo de Kotosh",
    "ubicacion": "Huánuco, Perú",
    "horario": "08:00-17:00",
    "aforo_maximo": 600,
}

DESDE = date(2024, 1, 1)
HASTA = date(2025, 12, 31)
SEMILLA = 42

# Probabilidad de lluvia por mes (1..12).
_PROB_LLUVIA: dict[int, float] = {
    12: 0.55, 1: 0.55, 2: 0.55, 3: 0.55,
    4: 0.30, 11: 0.30,
    5: 0.10, 6: 0.10, 7: 0.10, 8: 0.10, 9: 0.10, 10: 0.10,
}

_CLIMA_LLUVIA: tuple[tuple[str, ...], tuple[float, ...]] = (
    ("Lluvia ligera", "Lluvia fuerte"),
    (0.70, 0.30),
)
_CLIMA_SECO: tuple[tuple[str, ...], tuple[float, ...]] = (
    ("Soleado", "Parcialmente nublado", "Nublado"),
    (0.50, 0.30, 0.20),
)

_MULT_CLIMA: dict[str, float] = {
    "Soleado": 1.10,
    "Parcialmente nublado": 1.00,
    "Nublado": 0.90,
    "Lluvia ligera": 0.70,
    "Lluvia fuerte": 0.45,
}

_MULT_FERIADO_NACIONAL = 1.40
_MULT_FIESTA_LOCAL = 1.60
_MULT_VACACIONAL = 1.20

_TEMP_MIN = 22.0
_TEMP_MAX = 31.0
_DESCUENTO_LLUVIA = 3.0


def _rango_base(fecha: date) -> tuple[int, int]:
    """Rango de visitantes base segun el dia de la semana (weekday 0=Lunes)."""
    wd = fecha.weekday()
    if wd <= 3:  # Lunes..Jueves
        return 60, 90
    if wd == 4:  # Viernes
        return 90, 120
    if wd == 5:  # Sabado
        return 180, 260
    return 300, 420  # Domingo


def generar_visitas(desde: date, hasta: date, semilla: int = 42) -> list[dict]:
    """Genera una fila de visitas por dia en [desde, hasta] (ambos inclusive).

    Funcion pura y determinista: no toca la BD y, con la misma semilla, siempre
    devuelve el mismo resultado. Las filas no incluyen `lugar_id`.
    """
    if hasta < desde:
        raise ValueError("`hasta` debe ser mayor o igual que `desde`")

    rng = random.Random(semilla)
    filas: list[dict] = []

    fecha = desde
    while fecha <= hasta:
        # Clima segun el mes.
        llueve = rng.random() < _PROB_LLUVIA[fecha.month]
        opciones, pesos = _CLIMA_LLUVIA if llueve else _CLIMA_SECO
        clima = rng.choices(opciones, weights=pesos, k=1)[0]

        temp = round(rng.uniform(_TEMP_MIN, _TEMP_MAX), 1)
        if llueve:
            temp = round(temp - _DESCUENTO_LLUVIA, 1)

        # Calendario.
        es_feriado_nac = feriado_nacional(fecha) is not None
        es_fiesta = fiesta_local(fecha) is not None
        temporada_dia = temporada(fecha)

        # Visitantes = base x multiplicadores.
        lo, hi = _rango_base(fecha)
        base = rng.randint(lo, hi)

        mult = _MULT_CLIMA[clima]
        mult_evento = max(
            _MULT_FERIADO_NACIONAL if es_feriado_nac else 1.0,
            _MULT_FIESTA_LOCAL if es_fiesta else 1.0,
        )
        mult *= mult_evento
        if temporada_dia == "vacacional":
            mult *= _MULT_VACACIONAL

        filas.append(
            {
                "fecha": fecha,
                "dia_semana": dia_semana_es(fecha),
                "condicion_clima": clima,
                "temperatura_max": temp,
                "es_feriado": es_feriado_nac or es_fiesta,
                "temporada": temporada_dia,
                "visitantes_totales": max(0, round(base * mult)),
            }
        )
        fecha += timedelta(days=1)

    return filas


async def main() -> None:
    # Imports de BD aqui: `generar_visitas` debe poder importarse sin Postgres.
    from sqlalchemy.dialects.postgresql import insert

    from app.db.models import Base, LugarTuristico, VisitaHistorica
    from app.db.session import SessionLocal, engine

    # init.sql solo corre con el volumen vacio: aseguramos las tablas.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Upsert del lugar por `codigo`.
        stmt_lugar = (
            insert(LugarTuristico)
            .values(**LUGAR)
            .on_conflict_do_update(
                index_elements=[LugarTuristico.codigo],
                set_={k: v for k, v in LUGAR.items() if k != "codigo"},
            )
            .returning(LugarTuristico.id)
        )
        lugar_id = (await session.execute(stmt_lugar)).scalar_one()
        logger.info("Lugar %s listo (id=%s)", LUGAR["codigo"], lugar_id)

        filas = generar_visitas(DESDE, HASTA, semilla=SEMILLA)
        valores = [
            {
                **fila,
                "lugar_id": lugar_id,
                "temperatura_max": Decimal(str(fila["temperatura_max"])),
            }
            for fila in filas
        ]

        stmt_visitas = (
            insert(VisitaHistorica)
            .values(valores)
            .on_conflict_do_nothing(
                index_elements=[VisitaHistorica.lugar_id, VisitaHistorica.fecha]
            )
            .returning(VisitaHistorica.id)
        )
        insertadas = len((await session.execute(stmt_visitas)).scalars().all())

        await session.commit()

    logger.info("Insertadas %d visitas para %s", insertadas, LUGAR["nombre"])
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

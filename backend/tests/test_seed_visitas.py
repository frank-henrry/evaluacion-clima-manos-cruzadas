"""Pruebas del generador puro de visitas historicas (SPEC 03, paso 4).

No usan Postgres: `generar_visitas()` y `calendario_peru` son funciones puras.
"""

from datetime import date
from statistics import mean

import pytest

from app.data.calendario_peru import (
    dia_semana_es,
    feriado_nacional,
    fiesta_local,
    temporada,
)
from seed_visitas import generar_visitas

DESDE = date(2024, 1, 1)
HASTA = date(2025, 12, 31)

CLIMAS_VALIDOS = {
    "Soleado",
    "Parcialmente nublado",
    "Nublado",
    "Lluvia ligera",
    "Lluvia fuerte",
}
DIAS_ES = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


@pytest.fixture(scope="module")
def filas() -> list[dict]:
    return generar_visitas(DESDE, HASTA)


# --- generar_visitas --------------------------------------------------------


def test_genera_731_filas_con_fechas_unicas(filas):
    assert len(filas) == 731
    fechas = [f["fecha"] for f in filas]
    assert len(set(fechas)) == 731
    assert min(fechas) == DESDE
    assert max(fechas) == HASTA


def test_todas_las_condiciones_de_clima_son_validas(filas):
    assert {f["condicion_clima"] for f in filas} <= CLIMAS_VALIDOS


def test_misma_semilla_mismo_resultado():
    assert generar_visitas(DESDE, HASTA, semilla=42) == generar_visitas(
        DESDE, HASTA, semilla=42
    )


def test_semilla_distinta_resultado_distinto():
    assert generar_visitas(DESDE, HASTA, semilla=42) != generar_visitas(
        DESDE, HASTA, semilla=7
    )


def test_domingos_soleados_superan_a_lunes_con_lluvia_fuerte(filas):
    domingos_soleados = [
        f["visitantes_totales"]
        for f in filas
        if f["dia_semana"] == "Domingo" and f["condicion_clima"] == "Soleado"
    ]
    lunes_lluvia_fuerte = [
        f["visitantes_totales"]
        for f in filas
        if f["dia_semana"] == "Lunes" and f["condicion_clima"] == "Lluvia fuerte"
    ]
    assert domingos_soleados, "no hay domingos soleados en la muestra"
    assert lunes_lluvia_fuerte, "no hay lunes con lluvia fuerte en la muestra"
    assert mean(domingos_soleados) > mean(lunes_lluvia_fuerte)


@pytest.mark.parametrize("fecha", [date(2024, 6, 24), date(2025, 8, 15)])
def test_fiestas_locales_marcadas_como_feriado(filas, fecha):
    fila = next(f for f in filas if f["fecha"] == fecha)
    assert fila["es_feriado"] is True


def test_visitantes_no_negativos(filas):
    assert all(
        isinstance(f["visitantes_totales"], int) and f["visitantes_totales"] >= 0
        for f in filas
    )


def test_temporada_valida(filas):
    assert {f["temporada"] for f in filas} <= {"escolar", "vacacional"}


def test_dia_semana_coincide_con_fecha(filas):
    for f in filas:
        assert f["dia_semana"] == DIAS_ES[f["fecha"].weekday()], f["fecha"]


def test_hasta_menor_que_desde_lanza_value_error():
    with pytest.raises(ValueError):
        generar_visitas(date(2024, 1, 2), date(2024, 1, 1))


def test_un_solo_dia_devuelve_una_fila():
    filas = generar_visitas(date(2024, 3, 1), date(2024, 3, 1))
    assert len(filas) == 1
    assert filas[0]["fecha"] == date(2024, 3, 1)


# --- calendario_peru --------------------------------------------------------


@pytest.mark.parametrize("fecha", [date(2024, 3, 29), date(2025, 4, 18)])
def test_viernes_santo(fecha):
    assert feriado_nacional(fecha) == "Viernes Santo"


@pytest.mark.parametrize("fecha", [date(2024, 3, 28), date(2025, 4, 17)])
def test_jueves_santo(fecha):
    assert feriado_nacional(fecha) == "Jueves Santo"


def test_feriado_fijo_y_dia_normal():
    assert feriado_nacional(date(2024, 7, 28)) == "Fiestas Patrias"
    assert feriado_nacional(date(2024, 5, 10)) is None


def test_fiesta_local():
    assert fiesta_local(date(2024, 6, 24)) == "Fiesta de San Juan"
    assert fiesta_local(date(2025, 8, 15)) == "Aniversario de Huánuco"
    assert fiesta_local(date(2024, 6, 25)) is None


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2024, 2, 10), "vacacional"),
        (date(2024, 5, 10), "escolar"),
        (date(2024, 3, 15), "vacacional"),
        (date(2024, 3, 16), "escolar"),
        (date(2025, 12, 20), "vacacional"),
    ],
)
def test_temporada(fecha, esperado):
    assert temporada(fecha) == esperado


def test_dia_semana_es():
    assert dia_semana_es(date(2024, 1, 1)) == "Lunes"
    assert dia_semana_es(date(2024, 1, 7)) == "Domingo"

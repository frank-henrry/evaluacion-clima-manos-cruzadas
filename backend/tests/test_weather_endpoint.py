from datetime import datetime, timedelta, timezone

import httpx
import pytest
from jose import jwt

from app.api.dependencies import get_weather_service
from app.core.config import get_settings
from app.core.exceptions import (
    LocationNotFoundError,
    WeatherProviderResponseError,
    WeatherProviderUnavailableError,
)
from app.core.security import create_access_token
from app.main import app
from app.models.weather import WeatherResponse


class StubWeatherService:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.received_location: str | None = None

    async def get_weather(self, location: str) -> WeatherResponse:
        self.received_location = location
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=app)


@pytest.fixture
def auth_header() -> dict[str, str]:
    token = create_access_token("usuario@practica.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_consulta_exitosa_exige_jwt_y_normaliza_la_ciudad(
    transport: httpx.ASGITransport,
    auth_header: dict[str, str],
) -> None:
    service = StubWeatherService(
        WeatherResponse(
            location="Bogota",
            temperature="20°C",
            condition="Lluvia",
            humidity="80%",
        )
    )

    async def override_weather_service() -> StubWeatherService:
        return service

    app.dependency_overrides[get_weather_service] = override_weather_service
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/weather",
                params={"location": "  Bogotá  "},
                headers=auth_header,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "location": "Bogota",
        "temperature": "20°C",
        "condition": "Lluvia",
        "humidity": "80%",
    }
    assert service.received_location == "Bogotá"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer token-invalido"},
    ],
)
async def test_rechaza_solicitudes_sin_jwt_valido(
    transport: httpx.ASGITransport,
    headers: dict[str, str],
) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/weather", params={"location": "Lima"}, headers=headers
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado."}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_rechaza_jwt_expirado(transport: httpx.ASGITransport) -> None:
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "usuario@practica.com",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/weather",
            params={"location": "Lima"},
            headers={"Authorization": f"Bearer {expired}"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["   ", "x" * 101, "Li\x00ma"])
async def test_valida_location_despues_de_strip(
    transport: httpx.ASGITransport,
    auth_header: dict[str, str],
    location: str,
) -> None:
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/weather", params={"location": location}, headers=auth_header
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (LocationNotFoundError(), 404),
        (WeatherProviderResponseError(), 502),
        (WeatherProviderUnavailableError(), 503),
    ],
)
async def test_sanea_errores_del_proveedor(
    transport: httpx.ASGITransport,
    auth_header: dict[str, str],
    error: Exception,
    expected_status: int,
) -> None:
    async def override_weather_service() -> StubWeatherService:
        return StubWeatherService(error=error)

    app.dependency_overrides[get_weather_service] = override_weather_service
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/weather",
                params={"location": "Lima"},
                headers=auth_header,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert "weatherapi" not in response.text.lower()

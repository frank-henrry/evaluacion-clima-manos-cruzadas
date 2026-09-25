import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import (
    LocationNotFoundError,
    WeatherProviderResponseError,
    WeatherProviderUnavailableError,
)
from app.integrations.weather_api import WeatherApiClient


def make_client(handler) -> WeatherApiClient:
    settings = Settings(
        jwt_secret="test-secret",
        weather_api_key="provider-test-key",
        weather_api_base_url="https://weather.test/v1",
        weather_api_timeout_seconds=1,
    )
    return WeatherApiClient(settings, transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_get_current_envia_ciudad_idioma_y_parsea_respuesta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/current.json"
        assert request.url.params["q"] == "Bogotá"
        assert request.url.params["lang"] == "es"
        assert request.url.params["key"] == "provider-test-key"
        return httpx.Response(
            200,
            json={
                "location": {"name": "Bogota", "country": "Colombia"},
                "current": {
                    "temp_c": 21.5,
                    "condition": {"text": "Parcialmente nublado"},
                    "humidity": 71,
                },
            },
        )

    result = await make_client(handler).get_current("Bogotá")

    assert result.location.name == "Bogota"
    assert result.current.temp_c == 21.5
    assert result.current.humidity == 71


@pytest.mark.asyncio
async def test_codigo_1006_se_traduce_a_ciudad_no_encontrada() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"code": 1006, "message": "No matching location found."}},
        )

    with pytest.raises(LocationNotFoundError):
        await make_client(handler).get_current("NoExiste")


@pytest.mark.asyncio
async def test_payload_incompleto_se_traduce_a_respuesta_invalida() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"location": {"name": "Lima"}})

    with pytest.raises(WeatherProviderResponseError):
        await make_client(handler).get_current("Lima")


@pytest.mark.asyncio
async def test_error_de_red_se_traduce_a_proveedor_no_disponible() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("fallo simulado", request=request)

    with pytest.raises(WeatherProviderUnavailableError):
        await make_client(handler).get_current("Lima")


@pytest.mark.asyncio
async def test_key_ausente_no_realiza_peticion() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    settings = Settings(jwt_secret="test-secret", weather_api_key="")
    client = WeatherApiClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(WeatherProviderUnavailableError):
        await client.get_current("Lima")
    assert called is False

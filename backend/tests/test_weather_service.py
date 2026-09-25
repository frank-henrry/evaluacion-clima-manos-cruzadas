import pytest

from app.models.weather import WeatherApiResponse
from app.services.weather_service import WeatherService


class StubWeatherClient:
    async def get_current(self, location: str) -> WeatherApiResponse:
        assert location == "Lima"
        return WeatherApiResponse.model_validate(
            {
                "location": {"name": "Lima"},
                "current": {
                    "temp_c": 24.0,
                    "condition": {"text": "Despejado"},
                    "humidity": 60,
                },
            }
        )


@pytest.mark.asyncio
async def test_service_formatea_el_contrato_publico_con_strings() -> None:
    result = await WeatherService(StubWeatherClient()).get_weather("Lima")  # type: ignore[arg-type]

    assert result.model_dump() == {
        "location": "Lima",
        "temperature": "24°C",
        "condition": "Despejado",
        "humidity": "60%",
    }

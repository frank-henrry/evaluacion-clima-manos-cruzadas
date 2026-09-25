"""Caso de uso de consulta meteorologica."""

from app.integrations.weather_api import WeatherApiClient
from app.models.weather import WeatherResponse


class WeatherService:
    def __init__(self, client: WeatherApiClient) -> None:
        self._client = client

    async def get_weather(self, location: str) -> WeatherResponse:
        result = await self._client.get_current(location)
        current = result.current

        return WeatherResponse(
            location=result.location.name.strip(),
            temperature=f"{_format_number(current.temp_c)}°C",
            condition=current.condition.text.strip(),
            humidity=f"{current.humidity}%",
        )


def _format_number(value: float) -> str:
    """Evita publicar 24.0°C, pero conserva decimales significativos."""
    return f"{value:g}"

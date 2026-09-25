"""Cliente asincrono y saneado para WeatherAPI current.json y forecast.json."""

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    LocationNotFoundError,
    WeatherProviderResponseError,
    WeatherProviderUnavailableError,
)
from app.models.prediccion import WeatherApiForecastResponse
from app.models.weather import WeatherApiResponse

_LOCATION_NOT_FOUND_CODE = 1006


class WeatherApiClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = settings.weather_api_key.get_secret_value()
        self._base_url = settings.weather_api_base_url.rstrip("/")
        self._timeout = settings.weather_api_timeout_seconds
        self._transport = transport

    async def get_current(self, location: str) -> WeatherApiResponse:
        if not self._api_key:
            raise WeatherProviderUnavailableError

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    "/current.json",
                    params={"key": self._api_key, "q": location, "lang": "es"},
                )
        except httpx.RequestError as exc:
            raise WeatherProviderUnavailableError from exc

        if response.status_code >= 400:
            if self._provider_error_code(response) == _LOCATION_NOT_FOUND_CODE:
                raise LocationNotFoundError
            raise WeatherProviderUnavailableError

        try:
            return WeatherApiResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise WeatherProviderResponseError from exc

    async def fetch_forecast(
        self, location: str, days: int
    ) -> WeatherApiForecastResponse:
        """Pronostico diario de `days` dias (hoy incluido) para `location`.

        Mismo manejo de errores que `get_current`: solo lanza excepciones de
        dominio (`WeatherError`) y nunca expone la key ni el mensaje externo.
        """
        if not self._api_key:
            raise WeatherProviderUnavailableError

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    "/forecast.json",
                    params={
                        "key": self._api_key,
                        "q": location,
                        "days": days,
                        "lang": "es",
                    },
                )
        except httpx.RequestError as exc:
            raise WeatherProviderUnavailableError from exc

        if response.status_code >= 400:
            if self._provider_error_code(response) == _LOCATION_NOT_FOUND_CODE:
                raise LocationNotFoundError
            raise WeatherProviderUnavailableError

        try:
            return WeatherApiForecastResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise WeatherProviderResponseError from exc

    @staticmethod
    def _provider_error_code(response: httpx.Response) -> int | None:
        """Extrae solo el codigo; el mensaje externo nunca sale de esta capa."""
        try:
            body = response.json()
            code = body.get("error", {}).get("code")
            return code if isinstance(code, int) else None
        except (ValueError, AttributeError):
            return None

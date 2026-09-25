"""Modelos del contrato publico y de la respuesta de WeatherAPI."""

from pydantic import BaseModel, ConfigDict, Field


class WeatherResponse(BaseModel):
    """Respuesta publica de GET /api/v1/weather."""

    location: str
    temperature: str
    condition: str
    humidity: str


class WeatherApiLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)


class WeatherApiCondition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1)


class WeatherApiCurrent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    temp_c: float
    condition: WeatherApiCondition
    humidity: int = Field(ge=0, le=100)


class WeatherApiResponse(BaseModel):
    """Subconjunto de current.json que consume la aplicacion."""

    model_config = ConfigDict(extra="ignore")

    location: WeatherApiLocation
    current: WeatherApiCurrent

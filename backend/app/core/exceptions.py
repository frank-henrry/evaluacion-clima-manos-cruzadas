"""Excepciones de dominio. No conocen HTTP; el router las traduce a respuestas."""


class AuthError(Exception):
    """Fallo de autenticacion.

    Se usa el MISMO mensaje generico tanto si el correo no existe como si la
    contrasena es incorrecta: no se filtra cual de los dos fallo.
    """

    def __init__(self, message: str = "Correo o contraseña incorrectos.") -> None:
        super().__init__(message)
        self.message = message


class WeatherError(Exception):
    """Error base de dominio para una consulta meteorologica."""


class LocationNotFoundError(WeatherError):
    """WeatherAPI no reconoce la ciudad solicitada."""


class WeatherProviderUnavailableError(WeatherError):
    """WeatherAPI no esta disponible o no se encuentra configurado."""


class WeatherProviderResponseError(WeatherError):
    """WeatherAPI respondio con un payload que no cumple el contrato esperado."""

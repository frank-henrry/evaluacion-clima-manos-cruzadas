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


class ContextoNoDisponibleError(Exception):
    """No hay datos (pronostico ni historicos) para construir el contexto pedido."""


class HistoricosNoDisponiblesError(Exception):
    """No hay dias historicos del lugar para ese dia de la semana (nivel 4 vacio)."""


class AnalistaError(Exception):
    """Error base de dominio del Agente Analista (SPEC 06)."""


class AnalistaNoDisponibleError(AnalistaError):
    """El LLM no esta disponible: key vacia, timeout o error de la API de OpenAI."""


class AnalistaRespuestaInvalidaError(AnalistaError):
    """El LLM respondio algo que no cumple `PrediccionLLM` (schema o rangos)."""


class FiltrosInvalidosError(Exception):
    """Combinacion de filtros del historico no permitida (SPEC 09)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class HistoricoNoDisponibleError(Exception):
    """El lugar turistico configurado no existe: no hay historico que consultar."""

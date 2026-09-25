const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export class WeatherError extends Error {
  constructor(message, code = 'WEATHER_ERROR') {
    super(message);
    this.name = 'WeatherError';
    this.code = code;
  }
}

const ERROR_MESSAGES = {
  400: 'La ubicación seleccionada no es válida.',
  404: 'No se encontró información para la ciudad seleccionada.',
  422: 'Seleccioná una ciudad válida.',
  429: 'Se alcanzó el límite de consultas. Intentá más tarde.',
  502: 'El proveedor del clima devolvió una respuesta inválida.',
  503: 'El servicio meteorológico no está disponible temporalmente.',
  504: 'La consulta tardó demasiado. Intentá de nuevo.',
};

/** Consulta el clima usando exclusivamente el JWT de la sesión activa. */
export async function getWeather({ location, token, signal }) {
  let response;
  try {
    const query = new URLSearchParams({ location });
    response = await fetch(`${API_URL}/api/v1/weather?${query}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new WeatherError('No se pudo conectar con el servidor.', 'NETWORK_ERROR');
  }

  if (response.status === 401) {
    throw new WeatherError('Tu sesión expiró. Iniciá sesión nuevamente.', 'UNAUTHORIZED');
  }
  if (!response.ok) {
    throw new WeatherError(
      ERROR_MESSAGES[response.status] || 'No se pudo consultar el clima. Intentá de nuevo.',
      `HTTP_${response.status}`
    );
  }

  try {
    const data = await response.json();
    if (!data.location || data.temperature == null || !data.condition || data.humidity == null) {
      throw new Error('invalid response');
    }
    return data;
  } catch {
    throw new WeatherError('El servidor devolvió datos meteorológicos inválidos.', 'INVALID_RESPONSE');
  }
}

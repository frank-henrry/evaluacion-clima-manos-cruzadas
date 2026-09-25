const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export class PrediccionError extends Error {
  constructor(message, code = 'PREDICCION_ERROR') {
    super(message);
    this.name = 'PrediccionError';
    this.code = code;
  }
}

const GENERIC_MESSAGE = 'No se pudo obtener la predicción. Intentá de nuevo.';

// Mensajes propios del cliente: nunca se muestra el `detail` del backend.
const ERROR_MESSAGES = {
  422: 'Ingresá una fecha válida.',
  502: 'El análisis devolvió un resultado inválido. Intentá de nuevo.',
  503: 'El servicio de predicción no está disponible temporalmente.',
};

const isNumber = (value) => typeof value === 'number' && Number.isFinite(value);

const FUENTES_PREDICCION = ['ia', 'estadistica'];

// Cada día similar debe traer lo que usa el gráfico (spec 07 §5).
const isValidDia = (dia) =>
  dia != null &&
  typeof dia === 'object' &&
  typeof dia.fecha === 'string' &&
  isNumber(dia.visitantes_totales) &&
  typeof dia.condicion_clima === 'string';

function isValidHistoricos(historicos) {
  return (
    historicos != null &&
    typeof historicos === 'object' &&
    Array.isArray(historicos.dias) &&
    historicos.dias.every(isValidDia)
  );
}

function isValidPrediccion(data) {
  if (!data || typeof data !== 'object') return false;
  const { contexto } = data;
  return (
    FUENTES_PREDICCION.includes(data.fuente_prediccion) &&
    isValidHistoricos(data.historicos) &&
    typeof data.fecha === 'string' &&
    typeof data.lugar === 'string' &&
    contexto != null &&
    typeof contexto === 'object' &&
    typeof contexto.dia_semana === 'string' &&
    typeof contexto.condicion_clima === 'string' &&
    isNumber(contexto.temperatura_max) &&
    isNumber(data.prediccion_estimada) &&
    isNumber(data.rango_minimo) &&
    isNumber(data.rango_maximo) &&
    typeof data.razonamiento_explicado === 'string'
  );
}

/** Solicita la predicción de visitantes para `fecha` (YYYY-MM-DD) con el JWT de la sesión. */
export async function getPrediccion({ fecha, token, signal }) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/v1/predicciones`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ fecha }),
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new PrediccionError(GENERIC_MESSAGE, 'NETWORK_ERROR');
  }

  if (response.status === 401) {
    throw new PrediccionError('Tu sesión expiró. Iniciá sesión nuevamente.', 'UNAUTHORIZED');
  }
  if (!response.ok) {
    throw new PrediccionError(
      ERROR_MESSAGES[response.status] || GENERIC_MESSAGE,
      `HTTP_${response.status}`
    );
  }

  let data;
  try {
    data = await response.json();
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new PrediccionError(GENERIC_MESSAGE, 'INVALID_RESPONSE');
  }
  if (!isValidPrediccion(data)) {
    throw new PrediccionError(GENERIC_MESSAGE, 'INVALID_RESPONSE');
  }
  return data;
}

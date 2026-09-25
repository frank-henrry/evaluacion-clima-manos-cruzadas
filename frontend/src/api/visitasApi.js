const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export class VisitasError extends Error {
  constructor(message, code = 'VISITAS_ERROR') {
    super(message);
    this.name = 'VisitasError';
    this.code = code;
  }
}

const GENERIC_MESSAGE = 'No se pudo cargar el histórico. Intentá de nuevo.';

// Mensajes propios del cliente (spec 09 §4): nunca se muestra el `detail` del backend.
const ERROR_MESSAGES = {
  422: 'Revisá los filtros seleccionados.',
  503: 'El histórico no está disponible temporalmente.',
};

const isNumber = (value) => typeof value === 'number' && Number.isFinite(value);
const isNullableNumber = (value) => value === null || isNumber(value);
const isNullableString = (value) => value === null || value === undefined || typeof value === 'string';
const isObject = (value) => value != null && typeof value === 'object' && !Array.isArray(value);

const isValidItem = (item) =>
  isObject(item) &&
  typeof item.fecha === 'string' &&
  typeof item.dia_semana === 'string' &&
  typeof item.condicion_clima === 'string' &&
  isNullableNumber(item.temperatura_max) &&
  typeof item.es_feriado === 'boolean' &&
  isNullableString(item.temporada) &&
  isNumber(item.visitantes_totales);

const isValidResumen = (resumen) =>
  resumen === null ||
  (isObject(resumen) &&
    isNumber(resumen.promedio) &&
    isNumber(resumen.minimo) &&
    isNumber(resumen.maximo) &&
    isNumber(resumen.total_visitantes));

function isValidVisitas(data) {
  return (
    isObject(data) &&
    typeof data.lugar === 'string' &&
    isObject(data.filtros) &&
    typeof data.orden === 'string' &&
    typeof data.direccion === 'string' &&
    isNumber(data.pagina) &&
    isNumber(data.tamano) &&
    isNumber(data.total) &&
    isNumber(data.total_paginas) &&
    isValidResumen(data.resumen) &&
    Array.isArray(data.items) &&
    data.items.every(isValidItem)
  );
}

const isEmpty = (value) => value === undefined || value === null || value === '';

/** Arma la query omitiendo los parámetros vacíos (spec 09 §5). */
export function buildVisitasQuery({ filtros = {}, orden, direccion, pagina, tamano } = {}) {
  const params = new URLSearchParams();
  const entries = [
    ['fecha', filtros.fecha],
    ['anio', filtros.anio],
    ['mes', filtros.mes],
    ['orden', orden],
    ['direccion', direccion],
    ['pagina', pagina],
    ['tamano', tamano],
  ];
  entries.forEach(([key, value]) => {
    if (!isEmpty(value)) params.set(key, String(value));
  });
  return params.toString();
}

/**
 * Consulta el histórico de visitas de Las Manos Cruzadas con el JWT de la sesión.
 * `filtros`: `{ fecha? }` | `{ anio?, mes? }`. Los valores vacíos no se envían.
 */
export async function getVisitas({ filtros = {}, orden, direccion, pagina, tamano, token, signal }) {
  const query = buildVisitasQuery({ filtros, orden, direccion, pagina, tamano });
  const url = `${API_URL}/api/v1/visitas${query ? `?${query}` : ''}`;

  let response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new VisitasError(GENERIC_MESSAGE, 'NETWORK_ERROR');
  }

  if (response.status === 401) {
    throw new VisitasError('Tu sesión expiró. Iniciá sesión nuevamente.', 'UNAUTHORIZED');
  }
  if (!response.ok) {
    throw new VisitasError(
      ERROR_MESSAGES[response.status] || GENERIC_MESSAGE,
      `HTTP_${response.status}`
    );
  }

  let data;
  try {
    data = await response.json();
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new VisitasError(GENERIC_MESSAGE, 'INVALID_RESPONSE');
  }
  if (!isValidVisitas(data)) {
    throw new VisitasError(GENERIC_MESSAGE, 'INVALID_RESPONSE');
  }
  return data;
}

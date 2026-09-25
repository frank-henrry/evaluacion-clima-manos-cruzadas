import { useCallback, useEffect, useRef, useState } from 'react';
import { getVisitas, VisitasError } from '../api/visitasApi.js';

const GENERIC_MESSAGE = 'No se pudo cargar el histórico. Intentá de nuevo.';

export const ORDEN_DEFAULT = 'fecha';
export const DIRECCION_DEFAULT = 'desc';
const FILTROS_VACIOS = {};

/** Deja solo las claves con valor (`fecha` | `anio` [+ `mes`]). */
function normalizarFiltros(filtros = {}) {
  const limpio = {};
  ['fecha', 'anio', 'mes'].forEach((key) => {
    const value = filtros[key];
    if (value !== undefined && value !== null && value !== '') limpio[key] = value;
  });
  return limpio;
}

/**
 * Estado de la sección Histórico: loading | success | error.
 * Carga automáticamente la vista por defecto (Todo, fecha desc, página 1) y
 * vuelve a consultar cada vez que cambian filtros, orden o página.
 */
export function useVisitas({ token, onUnauthorized }) {
  const [filtros, setFiltros] = useState(FILTROS_VACIOS);
  const [orden, setOrden] = useState(ORDEN_DEFAULT);
  const [direccion, setDireccion] = useState(DIRECCION_DEFAULT);
  const [pagina, setPagina] = useState(1);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const onUnauthorizedRef = useRef(onUnauthorized);

  useEffect(() => {
    onUnauthorizedRef.current = onUnauthorized;
  }, [onUnauthorized]);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    setStatus('loading');
    setError('');

    getVisitas({ filtros, orden, direccion, pagina, token, signal: controller.signal })
      .then((result) => {
        if (controller.signal.aborted) return;
        setData(result);
        setStatus('success');
      })
      .catch((requestError) => {
        if (requestError?.name === 'AbortError' || controller.signal.aborted) return;
        if (requestError instanceof VisitasError && requestError.code === 'UNAUTHORIZED') {
          onUnauthorizedRef.current?.(requestError.message);
          return;
        }
        setData(null);
        setError(requestError instanceof VisitasError ? requestError.message : GENERIC_MESSAGE);
        setStatus('error');
      });

    return () => controller.abort();
  }, [token, filtros, orden, direccion, pagina, reloadKey]);

  const aplicarFiltros = useCallback((nuevos) => {
    setFiltros(normalizarFiltros(nuevos));
    setPagina(1);
  }, []);

  const limpiar = useCallback(() => {
    setFiltros(FILTROS_VACIOS);
    setPagina(1);
  }, []);

  const ordenar = useCallback(
    (columna) => {
      if (columna === orden) {
        setDireccion((actual) => (actual === 'desc' ? 'asc' : 'desc'));
      } else {
        setOrden(columna);
        setDireccion('desc');
      }
      setPagina(1);
    },
    [orden]
  );

  const irAPagina = useCallback((n) => {
    const destino = Number(n);
    if (!Number.isInteger(destino) || destino < 1) return;
    setPagina(destino);
  }, []);

  const reintentar = useCallback(() => setReloadKey((key) => key + 1), []);

  return {
    filtros,
    orden,
    direccion,
    pagina,
    data,
    status,
    error,
    isLoading: status === 'loading',
    aplicarFiltros,
    limpiar,
    ordenar,
    irAPagina,
    reintentar,
  };
}

import { useCallback, useEffect, useRef, useState } from 'react';
import { getPrediccion, PrediccionError } from '../api/prediccionApi.js';

const GENERIC_MESSAGE = 'No se pudo obtener la predicción. Intentá de nuevo.';

/** Estado de la pantalla de predicción: idle | loading | success | error. */
export function usePrediccion({ token, onUnauthorized }) {
  const [fecha, setFecha] = useState('');
  const [status, setStatus] = useState('idle');
  const [prediccion, setPrediccion] = useState(null);
  const [error, setError] = useState('');
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const selectFecha = useCallback((value) => {
    controllerRef.current?.abort();
    setFecha(value);
    setPrediccion(null);
    setError('');
    setStatus('idle');
  }, []);

  const predecir = useCallback(async () => {
    if (!fecha || !token) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus('loading');
    setError('');

    try {
      const result = await getPrediccion({ fecha, token, signal: controller.signal });
      if (controller.signal.aborted) return;
      setPrediccion(result);
      setStatus('success');
    } catch (requestError) {
      if (requestError?.name === 'AbortError' || controller.signal.aborted) return;
      if (requestError instanceof PrediccionError && requestError.code === 'UNAUTHORIZED') {
        onUnauthorized(requestError.message);
        return;
      }
      setPrediccion(null);
      setError(requestError instanceof PrediccionError ? requestError.message : GENERIC_MESSAGE);
      setStatus('error');
    }
  }, [fecha, onUnauthorized, token]);

  return {
    fecha,
    prediccion,
    error,
    status,
    isLoading: status === 'loading',
    selectFecha,
    predecir,
  };
}

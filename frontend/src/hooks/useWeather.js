import { useCallback, useEffect, useRef, useState } from 'react';
import { getWeather, WeatherError } from '../api/weatherApi.js';

export function useWeather({ token, onUnauthorized }) {
  const [location, setLocation] = useState('');
  const [status, setStatus] = useState('idle');
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState('');
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const selectLocation = useCallback((value) => {
    controllerRef.current?.abort();
    setLocation(value);
    setWeather(null);
    setError('');
    setStatus('idle');
  }, []);

  const consult = useCallback(async () => {
    if (!location || !token) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus('loading');
    setError('');

    try {
      const result = await getWeather({ location, token, signal: controller.signal });
      if (controller.signal.aborted) return;
      setWeather(result);
      setStatus('success');
    } catch (requestError) {
      if (requestError?.name === 'AbortError' || controller.signal.aborted) return;
      if (requestError instanceof WeatherError && requestError.code === 'UNAUTHORIZED') {
        onUnauthorized(requestError.message);
        return;
      }
      setWeather(null);
      setError(
        requestError instanceof WeatherError
          ? requestError.message
          : 'No se pudo consultar el clima. Intentá de nuevo.'
      );
      setStatus('error');
    }
  }, [location, onUnauthorized, token]);

  return {
    location,
    weather,
    error,
    status,
    isLoading: status === 'loading',
    selectLocation,
    consult,
  };
}

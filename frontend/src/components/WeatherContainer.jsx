import { useWeather } from '../hooks/useWeather.js';
import WeatherView from './WeatherView.jsx';

export default function WeatherContainer({ session, onLogout, onSessionExpired }) {
  const weatherState = useWeather({
    token: session.token,
    onUnauthorized: onSessionExpired,
  });

  return (
    <WeatherView
      correo={session.user.correo}
      location={weatherState.location}
      weather={weatherState.weather}
      error={weatherState.error}
      isLoading={weatherState.isLoading}
      onLocationChange={weatherState.selectLocation}
      onConsult={weatherState.consult}
      onLogout={onLogout}
    />
  );
}

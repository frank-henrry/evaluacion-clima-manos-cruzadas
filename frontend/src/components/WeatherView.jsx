import { CITIES } from '../data/cities.js';

export default function WeatherView({
  correo,
  location,
  weather,
  error,
  isLoading,
  onLocationChange,
  onConsult,
  onLogout,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();
    onConsult();
  };

  return (
    <section className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-md p-5 sm:p-8 space-y-7">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Consulta meteorológica</h1>
          <p className="mt-1 text-sm text-text-muted">
            Sesión de <span className="font-medium text-text">{correo}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="self-start rounded-lg border border-border px-4 py-2 text-sm font-medium text-text transition hover:bg-bg focus:outline-none focus:ring-2 focus:ring-ring"
        >
          Cerrar sesión
        </button>
      </header>

      <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
        <div className="space-y-1">
          <label htmlFor="weather-location" className="block text-sm font-medium text-text">
            Ciudad
          </label>
          <select
            id="weather-location"
            value={location}
            onChange={(event) => onLocationChange(event.target.value)}
            disabled={isLoading}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-text outline-none transition focus:ring-2 focus:ring-ring disabled:opacity-60"
          >
            <option value="">Seleccioná una ciudad</option>
            {CITIES.map((city) => (
              <option key={city.value} value={city.value}>{city.label}</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={!location || isLoading}
          className="rounded-lg bg-primary px-6 py-2.5 font-medium text-primary-text transition hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-60"
        >
          Consultar
        </button>
      </form>

      {isLoading && (
        <p role="status" aria-live="polite" className="rounded-lg border border-border bg-bg px-4 py-3 text-sm text-text-muted">
          Consultando…
        </p>
      )}

      {error && (
        <div role="alert" className="rounded-lg border border-error-border bg-error-bg px-4 py-3 text-sm text-error-text">
          <p>{error}</p>
          <button type="button" onClick={onConsult} className="mt-2 font-semibold underline focus:outline-none focus:ring-2 focus:ring-ring">
            Reintentar
          </button>
        </div>
      )}

      {weather && !isLoading && (
        <div aria-live="polite" className="rounded-xl border border-border bg-bg p-5">
          <h2 className="text-xl font-semibold text-text">{weather.location}</h2>
          <dl className="mt-5 grid gap-4 sm:grid-cols-3">
            <div><dt className="text-sm text-text-muted">Temperatura</dt><dd className="mt-1 text-2xl font-semibold text-text">{weather.temperature}</dd></div>
            <div><dt className="text-sm text-text-muted">Estado</dt><dd className="mt-1 text-lg font-medium text-text">{weather.condition}</dd></div>
            <div><dt className="text-sm text-text-muted">Humedad</dt><dd className="mt-1 text-2xl font-semibold text-text">{weather.humidity}</dd></div>
          </dl>
        </div>
      )}
    </section>
  );
}

/**
 * PRESENTACIONAL: selector de fecha + botón `Estimar afluencia`.
 * El botón queda deshabilitado sin fecha o mientras se analiza.
 */
export default function FormularioFecha({ fecha, isLoading, onFechaChange, onSubmit }) {
  const handleSubmit = (event) => {
    event.preventDefault();
    if (!fecha || isLoading) return;
    onSubmit();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-1.5">
          <label htmlFor="planificador-fecha" className="block text-sm font-medium text-text">
            Fecha
          </label>
          <input
            id="planificador-fecha"
            type="date"
            value={fecha}
            onChange={(event) => onFechaChange(event.target.value)}
            disabled={isLoading}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-text shadow-sm outline-none transition focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60 sm:max-w-xs"
          />
        </div>
        <button
          type="submit"
          disabled={!fecha || isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-6 py-2.5 font-medium text-primary-text shadow-sm transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="M7 15l4-4 3 3 5-6" />
          </svg>
          Estimar afluencia
        </button>
      </div>
    </form>
  );
}

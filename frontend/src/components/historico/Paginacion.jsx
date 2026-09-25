/**
 * PRESENTACIONAL: `Anterior` / `Siguiente` + `Página {p} de {n} · {total} registros`.
 * Los botones se deshabilitan en los extremos (o mientras carga).
 */
export default function Paginacion({ pagina, totalPaginas, total, isLoading, onCambiarPagina }) {
  const ultima = Math.max(totalPaginas, 1);
  const puedeAnterior = !isLoading && pagina > 1;
  const puedeSiguiente = !isLoading && pagina < totalPaginas;

  const buttonClass =
    'inline-flex items-center justify-center gap-1.5 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text shadow-sm transition hover:bg-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-surface';

  return (
    <nav
      aria-label="Paginación del histórico"
      className="flex flex-col items-center gap-3 sm:flex-row sm:justify-between"
    >
      <p className="text-sm text-text-muted" aria-live="polite">
        Página {pagina} de {ultima} · {total} registros
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onCambiarPagina(pagina - 1)}
          disabled={!puedeAnterior}
          className={buttonClass}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Anterior
        </button>
        <button
          type="button"
          onClick={() => onCambiarPagina(pagina + 1)}
          disabled={!puedeSiguiente}
          className={buttonClass}
        >
          Siguiente
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </div>
    </nav>
  );
}

import KpiCard from '../planificador/KpiCard.jsx';
import FiltrosHistorico from './FiltrosHistorico.jsx';
import TablaVisitas, { formatFecha } from './TablaVisitas.jsx';
import Paginacion from './Paginacion.jsx';

/**
 * PRESENTACIONAL: contenido de la sección Histórico.
 * Filtros + (carga | alerta | vacío | resumen, tabla y paginación).
 * Solo recibe props; no hace fetch.
 */

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

const iconProps = {
  viewBox: '0 0 24 24',
  className: 'h-4 w-4',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

const ICONS = {
  dias: (
    <svg {...iconProps}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </svg>
  ),
  promedio: (
    <svg {...iconProps}>
      <path d="M4 12h16" />
      <path d="M4 6h10M4 18h13" />
    </svg>
  ),
  minimo: (
    <svg {...iconProps}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  ),
  maximo: (
    <svg {...iconProps}>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
  ),
};

function describirPeriodo(filtros = {}) {
  if (filtros.fecha) return formatFecha(filtros.fecha);
  if (filtros.anio && filtros.mes) return `${MESES[filtros.mes - 1] ?? filtros.mes} ${filtros.anio}`;
  if (filtros.anio) return `Año ${filtros.anio}`;
  return 'Todos los registros';
}

function LoadingState() {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <p className="flex items-center gap-2 text-sm font-medium text-text-muted">
        <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-primary" />
        Cargando histórico…
      </p>
      <div aria-hidden="true" className="space-y-6">
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
              <div className="h-3 w-1/2 animate-pulse rounded bg-surface-muted" />
              <div className="mt-4 h-7 w-3/4 animate-pulse rounded bg-surface-muted" />
            </div>
          ))}
        </div>
        <div className="h-80 animate-pulse rounded-2xl border border-border bg-surface shadow-sm" />
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-2xl border border-error-border bg-error-bg p-5 text-error-text shadow-sm sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm font-medium">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="self-start rounded-lg border border-error-border bg-surface px-4 py-2 text-sm font-semibold text-error-text transition hover:bg-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-error-bg sm:self-auto"
      >
        Reintentar
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface-muted px-6 py-12 text-center">
      <p className="text-base font-medium text-text">No hay registros para los filtros seleccionados.</p>
      <p className="mt-1 text-sm text-text-muted">Probá con otro periodo o presioná «Limpiar».</p>
    </div>
  );
}

function Resultado({ data, filtros, orden, direccion, isLoading, onOrdenar, onCambiarPagina }) {
  const { resumen } = data;

  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted">
        Registros de <span className="font-medium text-text">{data.lugar}</span> ·{' '}
        <span className="font-medium text-text">{describirPeriodo(filtros)}</span>
      </p>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <KpiCard
          label="Días"
          value={data.total}
          detail={`${resumen.total_visitantes} visitantes en total`}
          icon={ICONS.dias}
        />
        <KpiCard label="Promedio" value={resumen.promedio} detail="visitantes por día" icon={ICONS.promedio} />
        <KpiCard label="Mínimo" value={resumen.minimo} detail="visitantes en un día" icon={ICONS.minimo} />
        <KpiCard label="Máximo" value={resumen.maximo} detail="visitantes en un día" icon={ICONS.maximo} />
      </div>

      <TablaVisitas items={data.items} orden={orden} direccion={direccion} onOrdenar={onOrdenar} />

      <Paginacion
        pagina={data.pagina}
        totalPaginas={data.total_paginas}
        total={data.total}
        isLoading={isLoading}
        onCambiarPagina={onCambiarPagina}
      />
    </div>
  );
}

export default function HistoricoView({
  filtros,
  orden,
  direccion,
  data,
  error,
  isLoading,
  onAplicarFiltros,
  onLimpiar,
  onOrdenar,
  onCambiarPagina,
  onReintentar,
}) {
  let content;
  if (error) {
    content = <ErrorState message={error} onRetry={onReintentar} />;
  } else if (isLoading && !data) {
    content = <LoadingState />;
  } else if (data && data.resumen === null) {
    content = isLoading ? <LoadingState /> : <EmptyState />;
  } else if (data) {
    // Recarga (orden / página / filtros): se mantiene la tabla atenuada y se anuncia la carga.
    content = (
      <div className="space-y-4">
        {isLoading && (
          <p role="status" aria-live="polite" className="flex items-center gap-2 text-sm font-medium text-text-muted">
            <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-primary" />
            Cargando histórico…
          </p>
        )}
        <div aria-busy={isLoading} className={`transition-opacity ${isLoading ? 'pointer-events-none opacity-60' : ''}`}>
          <Resultado
            data={data}
            filtros={filtros}
            orden={orden}
            direccion={direccion}
            isLoading={isLoading}
            onOrdenar={onOrdenar}
            onCambiarPagina={onCambiarPagina}
          />
        </div>
      </div>
    );
  } else {
    content = <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <FiltrosHistorico
        filtros={filtros}
        isLoading={isLoading}
        onAplicar={onAplicarFiltros}
        onLimpiar={onLimpiar}
      />
      {content}
    </div>
  );
}

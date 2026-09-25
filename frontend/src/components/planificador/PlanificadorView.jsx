import FormularioFecha from './FormularioFecha.jsx';
import KpiCard from './KpiCard.jsx';
import HistoricosChart from './HistoricosChart.jsx';
import RazonamientoCard from './RazonamientoCard.jsx';

/**
 * PRESENTACIONAL: contenido del Planificador de Visitas.
 * Formulario + (skeleton | alerta | KPIs, gráfico y razonamiento | vacío).
 * Solo recibe props; no hace fetch ni guarda estado.
 */

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
  visitantes: (
    <svg {...iconProps}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0" />
      <path d="M16 5a3 3 0 0 1 0 6M21 20a6 6 0 0 0-4-5.6" />
    </svg>
  ),
  rango: (
    <svg {...iconProps}>
      <path d="M4 12h16M7 8l-3 4 3 4M17 8l3 4-3 4" />
    </svg>
  ),
  clima: (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  ),
  dia: (
    <svg {...iconProps}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </svg>
  ),
};

/** 'YYYY-MM-DD' → 'dd/mm/aaaa'. */
function formatFechaLarga(fecha) {
  const [y, m, d] = String(fecha).split('-');
  return y && m && d ? `${d}/${m}/${y}` : String(fecha);
}

function SkeletonCard({ className = '' }) {
  return (
    <div className={`rounded-2xl border border-border bg-surface p-5 shadow-sm ${className}`}>
      <div className="h-3 w-1/2 animate-pulse rounded bg-surface-muted" />
      <div className="mt-4 h-7 w-3/4 animate-pulse rounded bg-surface-muted" />
      <div className="mt-3 h-3 w-1/3 animate-pulse rounded bg-surface-muted" />
    </div>
  );
}

function LoadingState() {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <p className="flex items-center gap-2 text-sm font-medium text-text-muted">
        <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-primary" />
        Analizando…
      </p>
      <div aria-hidden="true" className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="h-72 animate-pulse rounded-2xl border border-border bg-surface shadow-sm lg:col-span-2" />
          <div className="h-72 animate-pulse rounded-2xl border border-border bg-surface shadow-sm" />
        </div>
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
      <p className="text-base font-medium text-text">Todavía no hay una estimación</p>
      <p className="mt-1 text-sm text-text-muted">
        Elegí una fecha y presioná «Estimar afluencia» para ver los indicadores.
      </p>
    </div>
  );
}

function Resultado({ prediccion }) {
  const { contexto, historicos } = prediccion;
  const detalleDia = contexto.nombre_feriado
    ? contexto.nombre_feriado
    : contexto.temporada
      ? `Temporada ${contexto.temporada}`
      : null;

  return (
    <div aria-live="polite" className="space-y-6">
      <p className="text-sm text-text-muted">
        Estimación para <span className="font-medium text-text">{prediccion.lugar}</span> ·{' '}
        <span className="font-medium text-text">{formatFechaLarga(prediccion.fecha)}</span>
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Visitantes estimados"
          value={`≈ ${prediccion.prediccion_estimada}`}
          detail="visitantes"
          icon={ICONS.visitantes}
        />
        <KpiCard
          label="Rango esperado"
          value={`${prediccion.rango_minimo} – ${prediccion.rango_maximo}`}
          detail="mínimo – máximo"
          icon={ICONS.rango}
        />
        <KpiCard
          label="Clima"
          value={`${contexto.condicion_clima} · ${contexto.temperatura_max}°C`}
          detail="Temperatura máxima"
          badge={contexto.fuente_clima === 'estimado_historico' ? 'Estimado' : null}
          icon={ICONS.clima}
        />
        <KpiCard label="Día" value={contexto.dia_semana} detail={detalleDia} icon={ICONS.dia} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HistoricosChart
            dias={historicos.dias}
            cantidad={historicos.cantidad}
            nivelCoincidencia={historicos.nivel_coincidencia}
            prediccion={prediccion.prediccion_estimada}
          />
        </div>
        <RazonamientoCard
          texto={prediccion.razonamiento_explicado}
          fuente={prediccion.fuente_prediccion}
        />
      </div>
    </div>
  );
}

export default function PlanificadorView({
  fecha,
  prediccion,
  error,
  isLoading,
  onFechaChange,
  onPredecir,
}) {
  let content;
  if (isLoading) content = <LoadingState />;
  else if (error) content = <ErrorState message={error} onRetry={onPredecir} />;
  else if (prediccion) content = <Resultado prediccion={prediccion} />;
  else content = <EmptyState />;

  return (
    <div className="space-y-6">
      <FormularioFecha
        fecha={fecha}
        isLoading={isLoading}
        onFechaChange={onFechaChange}
        onSubmit={onPredecir}
      />
      {content}
    </div>
  );
}

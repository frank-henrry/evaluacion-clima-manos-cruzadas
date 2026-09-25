/**
 * PRESENTACIONAL: tarjeta de indicador.
 * `badge` (opcional) se muestra como etiqueta junto al título.
 */
export default function KpiCard({ label, value, detail, badge, icon }) {
  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon && (
            <span
              aria-hidden="true"
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary-soft-text"
            >
              {icon}
            </span>
          )}
          <h2 className="text-sm font-medium text-text-muted">{label}</h2>
        </div>
        {badge && (
          <span className="rounded-full border border-border bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-text">
            {badge}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold tracking-tight text-text">{value}</p>
      {detail && <p className="text-sm text-text-muted">{detail}</p>}
    </article>
  );
}

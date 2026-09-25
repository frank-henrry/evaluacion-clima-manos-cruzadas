const BADGES = {
  ia: {
    label: 'Análisis IA',
    className: 'bg-primary-soft text-primary-soft-text',
  },
  estadistica: {
    label: 'Estimación estadística',
    className: 'bg-surface-muted text-text-muted border border-border',
  },
};

/**
 * PRESENTACIONAL: razonamiento de la predicción con el badge de su origen
 * (`fuente` = "ia" | "estadistica").
 */
export default function RazonamientoCard({ texto, fuente }) {
  const badge = BADGES[fuente];

  return (
    <section
      aria-labelledby="razonamiento-titulo"
      className="flex h-full flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="razonamiento-titulo" className="text-base font-semibold text-text">
          Razonamiento
        </h2>
        {badge && (
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>
      <p className="text-sm leading-relaxed text-text">{texto}</p>
    </section>
  );
}

/**
 * PRESENTACIONAL: gráfico de barras en SVG propio (sin librerías).
 *  - Una barra por día similar, altura proporcional a `visitantes_totales`.
 *  - Eje X con la fecha `dd/mm/aa`; `<title>` por barra como tooltip nativo.
 *  - Línea horizontal punteada con la predicción (leyenda `Predicción`).
 * Es responsive: usa `viewBox` y escala al ancho del contenedor.
 */

const WIDTH = 640;
const HEIGHT = 260;
const PAD = { top: 16, right: 16, bottom: 34, left: 44 };
const PLOT_W = WIDTH - PAD.left - PAD.right;
const PLOT_H = HEIGHT - PAD.top - PAD.bottom;
const MAX_LABELS = 10;

/** 'YYYY-MM-DD' → 'dd/mm/aa' sin pasar por Date (evita corrimientos de zona horaria). */
export function formatFechaCorta(fecha) {
  const [y, m, d] = String(fecha).split('-');
  if (!y || !m || !d) return String(fecha);
  return `${d.slice(0, 2)}/${m}/${y.slice(-2)}`;
}

/** Tope "redondo" del eje Y (1, 2, 2.5, 5 × 10^n) y su paso entre 4 marcas. */
function niceScale(maxValue) {
  if (maxValue <= 0) return { max: 4, step: 1 };
  const rough = maxValue / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((f) => f * magnitude).find((s) => s * 4 >= maxValue);
  return { max: step * 4, step };
}

export default function HistoricosChart({ dias, cantidad, nivelCoincidencia, prediccion }) {
  const lista = Array.isArray(dias) ? dias : [];
  const total = Number.isFinite(cantidad) ? cantidad : lista.length;

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-text">Días similares ({total})</h2>
        {Number.isFinite(nivelCoincidencia) && (
          <p className="mt-0.5 text-sm text-text-muted">
            Nivel de coincidencia {nivelCoincidencia} de 4
          </p>
        )}
      </div>
      {lista.length > 0 && (
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-muted">
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="h-3 w-3 rounded-sm bg-primary" />
            <span>Visitantes</span>
          </li>
          <li className="flex items-center gap-1.5">
            <svg aria-hidden="true" width="18" height="6" viewBox="0 0 18 6">
              <line x1="0" y1="3" x2="18" y2="3" strokeWidth="2" strokeDasharray="4 3" className="stroke-accent" />
            </svg>
            <span>Predicción</span>
          </li>
        </ul>
      )}
    </div>
  );

  if (lista.length === 0) {
    return (
      <section className="flex h-full flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6">
        {header}
        <p className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border bg-surface-muted px-4 py-10 text-center text-sm text-text-muted">
          Sin días similares para graficar.
        </p>
      </section>
    );
  }

  const maxDato = Math.max(...lista.map((d) => d.visitantes_totales), Number.isFinite(prediccion) ? prediccion : 0);
  const { max: yMax, step } = niceScale(maxDato);
  const y = (value) => PAD.top + PLOT_H - (Math.max(value, 0) / yMax) * PLOT_H;

  const slot = PLOT_W / lista.length;
  const barW = Math.min(44, slot * 0.64);
  const labelEvery = Math.ceil(lista.length / MAX_LABELS);
  const ticks = Array.from({ length: 5 }, (_, i) => i * step);

  const ariaLabel =
    `Gráfico de barras con los visitantes de ${lista.length} días similares` +
    (Number.isFinite(prediccion) ? `; la predicción es de ${prediccion} visitantes.` : '.');

  return (
    <section className="flex h-full flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6">
      {header}
      <svg
        role="img"
        aria-label={ariaLabel}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        className="h-auto w-full"
      >
        {/* Grilla y eje Y */}
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              strokeWidth="1"
              className={tick === 0 ? 'stroke-border' : 'stroke-border opacity-60'}
            />
            <text
              x={PAD.left - 8}
              y={y(tick)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize="11"
              className="fill-text-muted"
            >
              {Math.round(tick)}
            </text>
          </g>
        ))}

        {/* Barras */}
        {lista.map((dia, index) => {
          const cx = PAD.left + slot * index + slot / 2;
          const top = y(dia.visitantes_totales);
          const fechaCorta = formatFechaCorta(dia.fecha);
          return (
            <g key={`${dia.fecha}-${index}`}>
              <rect
                x={cx - barW / 2}
                y={top}
                width={barW}
                height={Math.max(PAD.top + PLOT_H - top, 1)}
                rx="4"
                className="fill-primary opacity-90 transition-opacity hover:opacity-100"
              >
                <title>{`${fechaCorta} · ${dia.visitantes_totales} visitantes · ${dia.condicion_clima}`}</title>
              </rect>
              {index % labelEvery === 0 && (
                <text
                  x={cx}
                  y={HEIGHT - PAD.bottom + 18}
                  textAnchor="middle"
                  fontSize="11"
                  className="fill-text-muted"
                >
                  {fechaCorta}
                </text>
              )}
            </g>
          );
        })}

        {/* Línea de predicción */}
        {Number.isFinite(prediccion) && (
          <line
            x1={PAD.left}
            x2={WIDTH - PAD.right}
            y1={y(prediccion)}
            y2={y(prediccion)}
            strokeWidth="2"
            strokeDasharray="6 4"
            className="stroke-accent"
          />
        )}
      </svg>
    </section>
  );
}

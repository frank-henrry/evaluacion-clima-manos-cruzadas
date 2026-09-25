/**
 * PRESENTACIONAL: tabla de registros históricos.
 * Las cabeceras `Fecha` y `Visitantes` son botones que piden ordenar
 * (`onOrdenar(columna)`); el `<th>` expone `aria-sort`.
 * En pantallas chicas la tabla hace scroll horizontal.
 */

/** 'YYYY-MM-DD' → 'dd/mm/aaaa'. */
export function formatFecha(fecha) {
  const [y, m, d] = String(fecha).split('-');
  return y && m && d ? `${d}/${m}/${y}` : String(fecha);
}

function formatTemperatura(value) {
  if (typeof value !== 'number') return '—';
  return `${Number.isInteger(value) ? value : value.toFixed(1)}°C`;
}

function formatTemporada(value) {
  if (!value) return '—';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const thBase = 'whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-muted';

function SortableHeader({ columna, label, orden, direccion, onOrdenar, align = 'left' }) {
  const activa = orden === columna;
  const ariaSort = activa ? (direccion === 'asc' ? 'ascending' : 'descending') : 'none';
  const indicador = activa ? (direccion === 'asc' ? '▲' : '▼') : '▼';

  return (
    <th scope="col" aria-sort={ariaSort} className={`${thBase} ${align === 'right' ? 'text-right' : 'text-left'}`}>
      <button
        type="button"
        onClick={() => onOrdenar(columna)}
        className={`inline-flex items-center gap-1.5 rounded-md uppercase tracking-wide transition hover:text-text focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface ${
          activa ? 'text-text' : ''
        }`}
      >
        {label}
        <span aria-hidden="true" className={`text-[0.65rem] ${activa ? 'text-primary' : 'opacity-30'}`}>
          {indicador}
        </span>
      </button>
    </th>
  );
}

export default function TablaVisitas({ items, orden, direccion, onOrdenar }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <caption className="sr-only">Registros históricos de visitas</caption>
          <thead className="border-b border-border bg-surface-muted">
            <tr>
              <SortableHeader columna="fecha" label="Fecha" orden={orden} direccion={direccion} onOrdenar={onOrdenar} />
              <th scope="col" className={`${thBase} text-left`}>Día</th>
              <th scope="col" className={`${thBase} text-left`}>Clima</th>
              <th scope="col" className={`${thBase} text-right`}>Temp. máx.</th>
              <th scope="col" className={`${thBase} text-left`}>Feriado</th>
              <th scope="col" className={`${thBase} text-left`}>Temporada</th>
              <SortableHeader
                columna="visitantes"
                label="Visitantes"
                orden={orden}
                direccion={direccion}
                onOrdenar={onOrdenar}
                align="right"
              />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-text-muted">
                  No hay registros en esta página.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.fecha}
                  className="border-b border-border last:border-b-0 odd:bg-surface even:bg-surface-muted"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium tabular-nums text-text">
                    {formatFecha(item.fecha)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-text">{item.dia_semana}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-text">{item.condicion_clima}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums text-text">
                    {formatTemperatura(item.temperatura_max)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {item.es_feriado ? (
                      <span className="inline-flex rounded-full border border-border bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-text">
                        Sí
                      </span>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-text">{formatTemporada(item.temporada)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right font-semibold tabular-nums text-text">
                    {item.visitantes_totales}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

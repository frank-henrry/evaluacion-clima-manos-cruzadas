import { useEffect, useState } from 'react';

/**
 * PRESENTACIONAL (con estado local del formulario): filtros del histórico.
 * `Filtrar por`: Todo | Fecha | Mes | Año. El formulario solo emite los filtros
 * al pulsar `Aplicar filtros` (`onAplicar({ fecha } | { anio, mes } | { anio } | {})`).
 * Se re-sincroniza con los filtros aplicados (`filtros`) cuando cambian.
 */

const ANIO_MIN = 2000;
const ANIO_MAX = 2100;

const pad2 = (n) => String(n).padStart(2, '0');

function formDesdeFiltros(filtros = {}) {
  if (filtros.fecha) return { modo: 'fecha', fecha: filtros.fecha, mes: '', anio: '' };
  if (filtros.anio && filtros.mes) {
    return { modo: 'mes', fecha: '', mes: `${filtros.anio}-${pad2(filtros.mes)}`, anio: '' };
  }
  if (filtros.anio) return { modo: 'anio', fecha: '', mes: '', anio: String(filtros.anio) };
  return { modo: 'todo', fecha: '', mes: '', anio: '' };
}

const isFecha = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value);
const isMes = (value) => /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
const isAnio = (value) => {
  if (!/^\d{4}$/.test(value)) return false;
  const n = Number(value);
  return n >= ANIO_MIN && n <= ANIO_MAX;
};

/** Devuelve los filtros a enviar, o `null` si el valor del modo elegido no es válido. */
function construirFiltros(form) {
  switch (form.modo) {
    case 'fecha':
      return isFecha(form.fecha) ? { fecha: form.fecha } : null;
    case 'mes': {
      if (!isMes(form.mes)) return null;
      const [anio, mes] = form.mes.split('-');
      return { anio: Number(anio), mes: Number(mes) };
    }
    case 'anio':
      return isAnio(form.anio) ? { anio: Number(form.anio) } : null;
    default:
      return {};
  }
}

const controlClass =
  'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-text shadow-sm outline-none transition focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60';

export default function FiltrosHistorico({ filtros, isLoading, onAplicar, onLimpiar }) {
  const [form, setForm] = useState(() => formDesdeFiltros(filtros));

  useEffect(() => {
    setForm(formDesdeFiltros(filtros));
  }, [filtros]);

  const setCampo = (campo) => (event) => {
    const { value } = event.target;
    setForm((actual) => ({ ...actual, [campo]: value }));
  };

  const filtrosValidos = construirFiltros(form);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (isLoading || filtrosValidos === null) return;
    onAplicar(filtrosValidos);
  };

  const handleLimpiar = () => {
    setForm(formDesdeFiltros({}));
    onLimpiar();
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Filtros del histórico"
      className="rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
        <div className="space-y-1.5 lg:w-48">
          <label htmlFor="historico-modo" className="block text-sm font-medium text-text">
            Filtrar por
          </label>
          <select
            id="historico-modo"
            value={form.modo}
            onChange={setCampo('modo')}
            disabled={isLoading}
            className={controlClass}
          >
            <option value="todo">Todo</option>
            <option value="fecha">Fecha</option>
            <option value="mes">Mes</option>
            <option value="anio">Año</option>
          </select>
        </div>

        {form.modo === 'fecha' && (
          <div className="space-y-1.5 lg:w-56">
            <label htmlFor="historico-fecha" className="block text-sm font-medium text-text">
              Fecha
            </label>
            <input
              id="historico-fecha"
              type="date"
              value={form.fecha}
              onChange={setCampo('fecha')}
              disabled={isLoading}
              className={controlClass}
            />
          </div>
        )}

        {form.modo === 'mes' && (
          <div className="space-y-1.5 lg:w-56">
            <label htmlFor="historico-mes" className="block text-sm font-medium text-text">
              Mes
            </label>
            <input
              id="historico-mes"
              type="month"
              value={form.mes}
              onChange={setCampo('mes')}
              disabled={isLoading}
              placeholder="aaaa-mm"
              className={controlClass}
            />
          </div>
        )}

        {form.modo === 'anio' && (
          <div className="space-y-1.5 lg:w-40">
            <label htmlFor="historico-anio" className="block text-sm font-medium text-text">
              Año
            </label>
            <input
              id="historico-anio"
              type="number"
              inputMode="numeric"
              min={ANIO_MIN}
              max={ANIO_MAX}
              step="1"
              value={form.anio}
              onChange={setCampo('anio')}
              disabled={isLoading}
              placeholder="2025"
              className={controlClass}
            />
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row lg:ml-auto">
          <button
            type="submit"
            disabled={isLoading || filtrosValidos === null}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 font-medium text-primary-text shadow-sm transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 5h18l-7 8v6l-4 2v-8L3 5z" />
            </svg>
            Aplicar filtros
          </button>
          <button
            type="button"
            onClick={handleLimpiar}
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-lg border border-border bg-surface px-5 py-2.5 font-medium text-text transition hover:bg-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-60"
          >
            Limpiar
          </button>
        </div>
      </div>
    </form>
  );
}

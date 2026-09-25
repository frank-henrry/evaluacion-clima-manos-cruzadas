/**
 * Componente PRESENTACIONAL: boton para alternar tema claro/oscuro.
 * Solo recibe `theme` y `onToggle`; no toca localStorage ni el DOM.
 */
export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={isDark ? 'Activar tema claro' : 'Activar tema oscuro'}
      title={isDark ? 'Tema: oscuro' : 'Tema: claro'}
      className="inline-flex items-center gap-2 rounded-lg border border-border
        bg-surface px-3 py-1.5 text-sm font-medium text-text transition
        hover:bg-bg focus:outline-none focus:ring-2 focus:ring-ring
        focus:ring-offset-2 focus:ring-offset-bg"
    >
      <span aria-hidden="true">{isDark ? '🌙' : '☀️'}</span>
      <span>Tema: {isDark ? 'oscuro' : 'claro'}</span>
    </button>
  );
}

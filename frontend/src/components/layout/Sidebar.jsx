import ThemeToggle from '../ThemeToggle.jsx';

const navIconProps = {
  viewBox: '0 0 24 24',
  className: 'h-5 w-5 shrink-0',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
};

export const NAV_ITEMS = [
  {
    id: 'planificador',
    label: 'Planificador',
    icon: (
      <svg {...navIconProps}>
        <path d="M3 3v18h18" />
        <path d="M7 15l4-4 3 3 5-6" />
      </svg>
    ),
  },
  {
    id: 'historico',
    label: 'Histórico',
    icon: (
      <svg {...navIconProps}>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 9h18M9 9v11" />
      </svg>
    ),
  },
];

/**
 * PRESENTACIONAL: barra lateral del dashboard.
 * Marca, navegación (`Planificador` / `Histórico`), correo del usuario,
 * `ThemeToggle` y `Cerrar sesión`.
 * No conoce la sesión, el tema ni la sección: todo llega por props.
 */
export default function Sidebar({
  userEmail,
  theme,
  onToggleTheme,
  onLogout,
  activeSection = 'planificador',
  onNavigate = () => {},
}) {
  const initial = userEmail ? userEmail.charAt(0).toUpperCase() : '?';

  return (
    <div className="flex h-full flex-col gap-8 p-6">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-text shadow-sm"
        >
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 20h18" />
            <path d="M5 20l5-9 3 5 2-3 4 7" />
            <circle cx="16.5" cy="6.5" r="2" />
          </svg>
        </span>
        <div className="min-w-0">
          <p className="text-base font-semibold leading-tight text-text">Planificador de Visitas</p>
          <p className="mt-0.5 text-xs text-text-muted">Las Manos Cruzadas · Kotosh</p>
        </div>
      </div>

      <nav aria-label="Secciones">
        <ul className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive = item.id === activeSection;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={() => onNavigate(item.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface ${
                    isActive
                      ? 'bg-primary-soft text-primary-soft-text'
                      : 'text-text-muted hover:bg-bg hover:text-text'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-auto space-y-4">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-muted p-3">
          <span
            aria-hidden="true"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary-soft-text"
          >
            {initial}
          </span>
          <div className="min-w-0">
            <p className="text-xs text-text-muted">Sesión iniciada</p>
            <p className="truncate text-sm font-medium text-text" title={userEmail}>
              {userEmail}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text transition hover:bg-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="M16 17l5-5-5-5" />
              <path d="M21 12H9" />
            </svg>
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  );
}

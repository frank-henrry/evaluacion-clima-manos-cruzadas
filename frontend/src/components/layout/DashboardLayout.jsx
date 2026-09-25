import { useEffect, useState } from 'react';
import Sidebar from './Sidebar.jsx';

const SIDEBAR_ID = 'dashboard-sidebar';

// Cabecera de cada sección del dashboard.
const SECTION_HEADERS = {
  planificador: {
    title: 'Planificador de Visitas',
    subtitle: 'Estimá la afluencia de visitantes para organizar personal y recursos.',
  },
  historico: {
    title: 'Histórico de visitas',
    subtitle: 'Consultá y filtrá los registros de Las Manos Cruzadas.',
  },
};

/**
 * PRESENTACIONAL (con estado de UI local): estructura del dashboard.
 *  - md+: sidebar fija a la izquierda (`w-64`) y contenido a la derecha.
 *  - < md: barra superior con botón de menú (`aria-expanded`) que abre el
 *    sidebar como panel deslizante; se cierra con el mismo botón, tocando el
 *    fondo o con Escape.
 * El único estado que guarda es si el menú móvil está abierto; la sección
 * activa llega por props (`activeSection` / `onNavigate`). Al navegar desde
 * el panel móvil, el panel se cierra.
 */
export default function DashboardLayout({
  userEmail,
  theme,
  onToggleTheme,
  onLogout,
  activeSection = 'planificador',
  onNavigate = () => {},
  children,
}) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const header = SECTION_HEADERS[activeSection] ?? SECTION_HEADERS.planificador;

  const handleNavigate = (section) => {
    setIsMenuOpen(false);
    onNavigate(section);
  };

  useEffect(() => {
    if (!isMenuOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setIsMenuOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isMenuOpen]);

  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Barra superior (solo móvil) */}
      <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-surface px-4 md:hidden">
        <span className="flex items-center gap-2 text-sm font-semibold text-text">
          <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-primary" />
          Las Manos Cruzadas
        </span>
        <button
          type="button"
          aria-controls={SIDEBAR_ID}
          aria-expanded={isMenuOpen}
          aria-label={isMenuOpen ? 'Cerrar menú' : 'Abrir menú'}
          onClick={() => setIsMenuOpen((open) => !open)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border text-text transition hover:bg-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            {isMenuOpen ? (
              <path d="M6 6l12 12M18 6L6 18" />
            ) : (
              <path d="M4 7h16M4 12h16M4 17h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Fondo del panel móvil */}
      {isMenuOpen && (
        <div
          aria-hidden="true"
          onClick={() => setIsMenuOpen(false)}
          className="fixed inset-0 top-14 z-30 bg-text opacity-40 md:hidden"
        />
      )}

      <aside
        id={SIDEBAR_ID}
        aria-label="Barra lateral"
        className={`fixed bottom-0 left-0 top-14 z-40 w-64 border-r border-border bg-surface shadow-lg transition-transform duration-200 md:top-0 md:visible md:translate-x-0 md:shadow-none ${
          isMenuOpen ? 'visible translate-x-0' : 'invisible -translate-x-full'
        }`}
      >
        <Sidebar
          userEmail={userEmail}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onLogout={onLogout}
          activeSection={activeSection}
          onNavigate={handleNavigate}
        />
      </aside>

      <div className="md:pl-64">
        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-10 lg:py-10">
          <header className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-text sm:text-3xl">
              {header.title}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-text-muted sm:text-base">
              {header.subtitle}
            </p>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}

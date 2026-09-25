import { useEffect, useState } from 'react';
import { useLogin } from '../hooks/useLogin.js';
import LoginForm from './LoginForm.jsx';
import ThemeToggle from './ThemeToggle.jsx';
import DashboardLayout from './layout/DashboardLayout.jsx';
import PlanificadorContainer from './planificador/PlanificadorContainer.jsx';
import HistoricoContainer from './historico/HistoricoContainer.jsx';

/**
 * Componente CONTAINER: conecta el hook `useLogin` (estado + llamada a la
 * capa de datos) con los componentes de presentacion y elige la pantalla:
 *  - autenticado: `DashboardLayout` + la sección activa (`PlanificadorContainer`
 *    o `HistoricoContainer`, por defecto `planificador`);
 *  - sin sesión: `LoginForm` centrado con el `ThemeToggle` arriba.
 *
 * `theme` / `onToggleTheme` llegan desde `App` (hook `useTheme`).
 */
export default function LoginContainer({ theme = 'light', onToggleTheme = () => {} }) {
  const {
    fields,
    fieldErrors,
    formError,
    isLoading,
    isAuthenticated,
    session,
    setField,
    submit,
    logout,
    expireSession,
  } = useLogin();
  const [activeSection, setActiveSection] = useState('planificador');

  // Al cerrar o expirar la sesión, el próximo ingreso vuelve al Planificador.
  useEffect(() => {
    if (!isAuthenticated) setActiveSection('planificador');
  }, [isAuthenticated]);

  if (isAuthenticated) {
    return (
      <DashboardLayout
        userEmail={session.user.correo}
        theme={theme}
        onToggleTheme={onToggleTheme}
        onLogout={logout}
        activeSection={activeSection}
        onNavigate={setActiveSection}
      >
        {activeSection === 'historico' ? (
          <HistoricoContainer session={session} onSessionExpired={expireSession} />
        ) : (
          <PlanificadorContainer session={session} onSessionExpired={expireSession} />
        )}
      </DashboardLayout>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col items-center justify-center gap-4 p-4">
      <div className="w-full max-w-sm flex justify-end">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
      <LoginForm
        values={fields}
        fieldErrors={fieldErrors}
        formError={formError}
        isLoading={isLoading}
        onFieldChange={setField}
        onSubmit={submit}
      />
    </div>
  );
}

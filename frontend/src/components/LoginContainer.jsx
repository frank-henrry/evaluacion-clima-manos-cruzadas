import { useLogin } from '../hooks/useLogin.js';
import LoginForm from './LoginForm.jsx';
import WeatherContainer from './WeatherContainer.jsx';

/**
 * Componente CONTAINER: conecta el hook `useLogin` (estado + llamada a la
 * capa de datos) con los componentes de presentacion. No tiene markup propio
 * mas alla de elegir que pantalla mostrar.
 */
export default function LoginContainer() {
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

  if (isAuthenticated) {
    return (
      <WeatherContainer
        session={session}
        onLogout={logout}
        onSessionExpired={expireSession}
      />
    );
  }

  return (
    <LoginForm
      values={fields}
      fieldErrors={fieldErrors}
      formError={formError}
      isLoading={isLoading}
      onFieldChange={setField}
      onSubmit={submit}
    />
  );
}

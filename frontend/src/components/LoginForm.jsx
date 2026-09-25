/**
 * Componente PRESENTACIONAL del formulario de login.
 * Solo recibe props y renderiza UI. No hace fetch, no valida, no conoce authApi.
 * Los colores salen de las CSS vars via Tailwind (bg-surface, text-text, ...).
 */
export default function LoginForm({
  values,
  fieldErrors = {},
  formError = '',
  isLoading = false,
  onFieldChange,
  onSubmit,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-md p-8 space-y-6"
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-text">Iniciar sesión</h1>
        <p className="text-sm text-text-muted">
          Ingresá tu correo y contraseña para continuar.
        </p>
      </div>

      {formError && (
        <p
          role="alert"
          className="text-sm text-error-text bg-error-bg border border-error-border rounded-lg px-3 py-2"
        >
          {formError}
        </p>
      )}

      <div className="space-y-1">
        <label
          htmlFor="email"
          className="block text-sm font-medium text-text"
        >
          Correo
        </label>
        <input
          id="email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={values.email}
          onChange={(e) => onFieldChange('email', e.target.value)}
          disabled={isLoading}
          aria-invalid={Boolean(fieldErrors.email)}
          aria-describedby={fieldErrors.email ? 'email-error' : undefined}
          className={`w-full rounded-lg border px-3 py-2 bg-surface text-text outline-none transition
            focus:ring-2 focus:ring-ring disabled:opacity-60
            ${fieldErrors.email ? 'border-error-border' : 'border-border'}`}
        />
        {fieldErrors.email && (
          <p id="email-error" className="text-xs text-error-text">{fieldErrors.email}</p>
        )}
      </div>

      <div className="space-y-1">
        <label
          htmlFor="password"
          className="block text-sm font-medium text-text"
        >
          Contraseña
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={values.password}
          onChange={(e) => onFieldChange('password', e.target.value)}
          disabled={isLoading}
          aria-invalid={Boolean(fieldErrors.password)}
          aria-describedby={fieldErrors.password ? 'password-error' : undefined}
          className={`w-full rounded-lg border px-3 py-2 bg-surface text-text outline-none transition
            focus:ring-2 focus:ring-ring disabled:opacity-60
            ${fieldErrors.password ? 'border-error-border' : 'border-border'}`}
        />
        {fieldErrors.password && (
          <p id="password-error" className="text-xs text-error-text">{fieldErrors.password}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-primary-text
          transition hover:bg-primary-hover focus:outline-none focus:ring-2
          focus:ring-ring focus:ring-offset-2 focus:ring-offset-bg disabled:opacity-60"
      >
        {isLoading ? 'Iniciando sesión…' : 'Iniciar sesión'}
      </button>
    </form>
  );
}

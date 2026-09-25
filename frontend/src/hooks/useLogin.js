import { useCallback, useState } from 'react';
import { login as loginRequest, AuthError } from '../api/authApi.js';
import { validateLogin, hasErrors } from '../validation/validateLogin.js';

const EMPTY_FIELDS = { email: '', password: '' };

/**
 * Hook que concentra el estado del login y la llamada a la capa de datos.
 * Los componentes de presentacion no tocan authApi ni conocen la validacion:
 * solo consumen lo que expone este hook.
 */
export function useLogin() {
  const [fields, setFields] = useState(EMPTY_FIELDS);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [status, setStatus] = useState('idle'); // idle | loading | authenticated
  const [session, setSession] = useState(null); // { user, token }

  const setField = useCallback((name, value) => {
    setFields((prev) => ({ ...prev, [name]: value }));
    // Al editar, limpiamos el error puntual de ese campo y el error general.
    setFieldErrors((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
    setFormError('');
  }, []);

  const submit = useCallback(async () => {
    setFormError('');

    const errors = validateLogin(fields);
    setFieldErrors(errors);
    if (hasErrors(errors)) {
      return;
    }

    setStatus('loading');
    try {
      const result = await loginRequest({
        email: fields.email,
        password: fields.password,
      });
      setSession(result);
      setStatus('authenticated');
    } catch (err) {
      setStatus('idle');
      if (err instanceof AuthError) {
        // Mensaje ya saneado por la capa de datos (no expone internos).
        setFormError(err.message);
      } else {
        setFormError('No se pudo iniciar sesión. Intentá de nuevo.');
      }
    }
  }, [fields]);

  const logout = useCallback(() => {
    setFields(EMPTY_FIELDS);
    setFieldErrors({});
    setFormError('');
    setSession(null);
    setStatus('idle');
  }, []);

  const expireSession = useCallback((message) => {
    setFields(EMPTY_FIELDS);
    setFieldErrors({});
    setSession(null);
    setStatus('idle');
    setFormError(message || 'Tu sesión expiró. Iniciá sesión nuevamente.');
  }, []);

  return {
    fields,
    fieldErrors,
    formError,
    isLoading: status === 'loading',
    isAuthenticated: status === 'authenticated',
    session,
    setField,
    submit,
    logout,
    expireSession,
  };
}

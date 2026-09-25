const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export class AuthError extends Error {
  constructor(message, code = 'AUTH_ERROR') {
    super(message);
    this.name = 'AuthError';
    this.code = code;
  }
}

/** Inicia sesión contra el backend. Los componentes nunca acceden a fetch. */
export async function login({ email, password }) {
  let response;
  try {
    response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ correo: email, password }),
    });
  } catch {
    throw new AuthError('No se pudo conectar con el servidor.', 'NETWORK_ERROR');
  }

  if (response.status === 400 || response.status === 401) {
    throw new AuthError('Correo o contraseña incorrectos.', 'INVALID_CREDENTIALS');
  }
  if (!response.ok) {
    throw new AuthError('No se pudo iniciar sesión. Intentá de nuevo.', 'SERVER_ERROR');
  }

  try {
    const data = await response.json();
    if (!data.token || !data.correo) throw new Error('invalid response');
    return { user: { correo: data.correo }, token: data.token };
  } catch {
    throw new AuthError('El servidor devolvió una respuesta inválida.', 'INVALID_RESPONSE');
  }
}

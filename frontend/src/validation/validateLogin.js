/**
 * Validaciones de la spec 01-loginv2 (reglas del formulario de login).
 *
 * Reglas:
 *  - Ambos campos son obligatorios.
 *  - El correo no debe tener espacios en blanco.
 *  - El correo debe tener formato de email valido.
 *
 * Devuelve un objeto de errores { email?, password? }. Si esta vacio,
 * los datos son validos para intentar el login.
 */

// Regex simple: algo@algo.algo, sin espacios ni "@" repetidos.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLogin({ email, password }) {
  const errors = {};

  if (!email || email.trim() === '') {
    errors.email = 'El correo es obligatorio.';
  } else if (/\s/.test(email)) {
    errors.email = 'El correo no debe contener espacios en blanco.';
  } else if (!EMAIL_RE.test(email)) {
    errors.email = 'Ingresá un correo válido.';
  }

  if (!password || password === '') {
    errors.password = 'La contraseña es obligatoria.';
  }

  return errors;
}

export function hasErrors(errors) {
  return Object.keys(errors).length > 0;
}

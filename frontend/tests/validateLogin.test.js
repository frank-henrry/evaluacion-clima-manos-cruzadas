import { describe, it, expect } from 'vitest';
import { validateLogin, hasErrors } from '../src/validation/validateLogin.js';

describe('validateLogin', () => {
  it('exige ambos campos', () => {
    expect(validateLogin({ email: '', password: '' })).toEqual({
      email: 'El correo es obligatorio.',
      password: 'La contraseña es obligatoria.',
    });
  });

  it('rechaza espacios y formatos inválidos', () => {
    expect(validateLogin({ email: 'a @b.com', password: 'x' }).email).toMatch(/espacios/);
    expect(validateLogin({ email: 'invalido', password: 'x' }).email).toMatch(/correo válido/);
  });

  it('acepta un correo válido', () => {
    const errors = validateLogin({ email: 'admin@practica.com', password: 'x' });
    expect(errors).toEqual({});
    expect(hasErrors(errors)).toBe(false);
  });
});

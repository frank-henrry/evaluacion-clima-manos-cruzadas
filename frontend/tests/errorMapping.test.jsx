import { beforeEach, describe, expect, it, vi } from 'vitest';
import { login, AuthError } from '../src/api/authApi.js';
import { getWeather, WeatherError } from '../src/api/weatherApi.js';

beforeEach(() => vi.restoreAllMocks());

describe('mapeo seguro de errores HTTP', () => {
  it('login traduce credenciales inválidas sin exponer el body', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('detalle interno', { status: 401 }));
    await expect(login({ email: 'a@b.com', password: 'x' })).rejects.toMatchObject({
      message: 'Correo o contraseña incorrectos.',
      code: 'INVALID_CREDENTIALS',
    });
  });

  it('weather identifica una sesión no autorizada', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 401 }));
    await expect(getWeather({ location: 'Huanuco, Peru', token: 'x' })).rejects.toMatchObject({
      message: 'Tu sesión expiró. Iniciá sesión nuevamente.',
      code: 'UNAUTHORIZED',
    });
  });

  it('usa errores de dominio exportados', () => {
    expect(new AuthError('x')).toBeInstanceOf(Error);
    expect(new WeatherError('x')).toBeInstanceOf(Error);
  });
});

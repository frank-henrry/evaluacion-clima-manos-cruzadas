import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginContainer from '../src/components/LoginContainer.jsx';

beforeEach(() => {
  vi.restoreAllMocks();
});

async function login(user) {
  await user.type(screen.getByLabelText('Correo'), 'admin@practica.com');
  await user.type(screen.getByLabelText('Contraseña'), 'admin123');
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
}

describe('flujo login y clima', () => {
  it('autentica contra el backend y consulta una ciudad con Bearer', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ correo: 'admin@practica.com', token: 'jwt-123' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ location: 'Huanuco', temperature: '18°C', condition: 'Nublado', humidity: '70%' }), { status: 200 }));

    render(<LoginContainer />);
    await login(user);
    expect(await screen.findByRole('heading', { name: 'Consulta meteorológica' })).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toContain('/auth/login');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ correo: 'admin@practica.com', password: 'admin123' }),
    });

    await user.selectOptions(screen.getByLabelText('Ciudad'), 'Huanuco, Peru');
    await user.click(screen.getByRole('button', { name: 'Consultar' }));

    expect(await screen.findByText('18°C')).toBeInTheDocument();
    expect(screen.getByText('Nublado')).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/weather?location=Huanuco%2C+Peru');
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer jwt-123');
  });

  it('un 401 meteorológico elimina la sesión y avisa en login', async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ correo: 'admin@practica.com', token: 'jwt-123' }), { status: 200 }))
      .mockResolvedValueOnce(new Response('', { status: 401 }));

    render(<LoginContainer />);
    await login(user);
    await user.selectOptions(await screen.findByLabelText('Ciudad'), 'Tingo Maria, Peru');
    await user.click(screen.getByRole('button', { name: 'Consultar' }));

    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Tu sesión expiró');
  });

  it('bloquea Consultar sin ciudad y muestra carga durante la petición', async () => {
    const user = userEvent.setup();
    let resolveWeather;
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ correo: 'admin@practica.com', token: 'jwt-123' }), { status: 200 }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveWeather = resolve; }));

    render(<LoginContainer />);
    await login(user);
    const consultButton = await screen.findByRole('button', { name: 'Consultar' });
    expect(consultButton).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Ciudad'), 'Tingo Maria, Peru');
    await user.click(consultButton);
    expect(screen.getByRole('status')).toHaveTextContent('Consultando…');
    resolveWeather(new Response(JSON.stringify({ location: 'Tingo Maria', temperature: '20°C', condition: 'Soleado', humidity: '45%' }), { status: 200 }));
    await waitFor(() => expect(screen.getByText('20°C')).toBeInTheDocument());
  });

  it('muestra un error recuperable y permite reintentar', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ correo: 'admin@practica.com', token: 'jwt-123' }), { status: 200 }))
      .mockResolvedValueOnce(new Response('', { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ location: 'Huanuco', temperature: '24°C', condition: 'Despejado', humidity: '60%' }), { status: 200 }));

    render(<LoginContainer />);
    await login(user);
    await user.selectOptions(await screen.findByLabelText('Ciudad'), 'Huanuco, Peru');
    await user.click(screen.getByRole('button', { name: 'Consultar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible');
    await user.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('24°C')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

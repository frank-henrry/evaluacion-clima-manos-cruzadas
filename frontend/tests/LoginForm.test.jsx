import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginForm from '../src/components/LoginForm.jsx';

const baseProps = {
  values: { email: '', password: '' },
  fieldErrors: {},
  formError: '',
  isLoading: false,
  onFieldChange: vi.fn(),
  onSubmit: vi.fn(),
};

describe('LoginForm', () => {
  it('renderiza correo, contraseña y la acción requerida', () => {
    render(<LoginForm {...baseProps} />);
    expect(screen.getByLabelText('Correo')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeEnabled();
  });

  it('expone errores y estado de carga de forma accesible', () => {
    render(<LoginForm {...baseProps} fieldErrors={{ email: 'Correo inválido' }} formError="Error general" isLoading />);
    expect(screen.getByRole('alert')).toHaveTextContent('Error general');
    expect(screen.getByLabelText('Correo')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('button', { name: 'Iniciando sesión…' })).toBeDisabled();
  });

  it('notifica cambios y submit', async () => {
    const user = userEvent.setup();
    const onFieldChange = vi.fn();
    const onSubmit = vi.fn();
    render(<LoginForm {...baseProps} onFieldChange={onFieldChange} onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText('Correo'), 'a');
    await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
    expect(onFieldChange).toHaveBeenCalledWith('email', 'a');
    expect(onSubmit).toHaveBeenCalledOnce();
  });
});

import LoginContainer from './components/LoginContainer.jsx';
import { useTheme } from './hooks/useTheme.js';

/**
 * Punto de entrada. Solo resuelve el tema y lo delega a `LoginContainer`,
 * que decide dónde se muestra el `ThemeToggle`:
 *  - sin sesión: arriba a la derecha de la pantalla de login;
 *  - con sesión: dentro del `Sidebar` del `DashboardLayout`.
 * Así el toggle existe una sola vez por pantalla y el layout de cada una
 * (login centrado vs. dashboard a pantalla completa) no se pisan.
 */
export default function App() {
  const { theme, toggleTheme } = useTheme();

  return <LoginContainer theme={theme} onToggleTheme={toggleTheme} />;
}

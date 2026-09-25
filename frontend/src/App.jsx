import LoginContainer from './components/LoginContainer.jsx';
import ThemeToggle from './components/ThemeToggle.jsx';
import { useTheme } from './hooks/useTheme.js';

/** Punto de entrada: layout común para login y consulta meteorológica. */
export default function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col items-center justify-center gap-4 p-4">
      <div className="w-full max-w-2xl flex justify-end">
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </div>
      <LoginContainer />
    </div>
  );
}

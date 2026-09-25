import { useCallback, useEffect, useState } from 'react';

/**
 * Manejo del tema claro/oscuro SIN librerias.
 *
 * - `preference`: 'light' | 'dark' | null. `null` = seguir al sistema.
 * - El tema efectivo se aplica poniendo (o quitando) `data-theme` en
 *   `document.documentElement`; el CSS de `src/index.css` hace el resto.
 * - La preferencia manual se persiste en `localStorage` (envuelto en try/catch).
 * - Al cargar: si hay valor guardado se usa; si no, manda el sistema.
 */
const STORAGE_KEY = 'practica-1:theme';
const VALID = ['light', 'dark'];

function readStoredPreference() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return VALID.includes(value) ? value : null;
  } catch {
    return null;
  }
}

function getSystemTheme() {
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  } catch {
    return 'light';
  }
}

export function useTheme() {
  const [preference, setPreference] = useState(readStoredPreference);
  const [systemTheme, setSystemTheme] = useState(getSystemTheme);

  // Seguir los cambios del sistema mientras no haya override manual.
  useEffect(() => {
    let media;
    try {
      media = window.matchMedia('(prefers-color-scheme: dark)');
    } catch {
      return undefined;
    }
    const onChange = (event) =>
      setSystemTheme(event.matches ? 'dark' : 'light');
    media.addEventListener?.('change', onChange);
    return () => media.removeEventListener?.('change', onChange);
  }, []);

  // Tema realmente visible.
  const theme = preference ?? systemTheme;

  // Aplicar/quitar el atributo en <html>.
  useEffect(() => {
    const root = document.documentElement;
    if (preference) {
      root.setAttribute('data-theme', preference);
    } else {
      root.removeAttribute('data-theme');
    }
  }, [preference]);

  const setTheme = useCallback((next) => {
    const value = VALID.includes(next) ? next : null;
    setPreference(value);
    try {
      if (value) {
        window.localStorage.setItem(STORAGE_KEY, value);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Sin persistencia (modo privado, storage bloqueado): no es critico.
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [theme, setTheme]);

  return { theme, preference, setTheme, toggleTheme };
}

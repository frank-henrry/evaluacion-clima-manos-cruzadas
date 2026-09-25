import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Configuracion de test (Vitest). Se mantiene separada de vite.config.js;
// cuando existen ambos archivos, Vitest usa este.
export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom: DOM simulado para React Testing Library.
    environment: 'jsdom',
    // globals: describe/it/expect/vi disponibles sin import.
    globals: true,
    // setup: matchers de jest-dom + cleanup entre tests.
    setupFiles: './tests/setup.js',
    // No procesamos CSS (Tailwind) en los tests: no aporta y ralentiza.
    css: false,
    include: ['tests/**/*.{test,spec}.{js,jsx}'],
  },
});

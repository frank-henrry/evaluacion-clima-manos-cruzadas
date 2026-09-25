/**
 * Setup global de los tests.
 *  - Agrega los matchers de @testing-library/jest-dom (toBeInTheDocument, etc.).
 *  - Limpia el DOM y los mocks despues de cada test para que no se filtre estado.
 */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

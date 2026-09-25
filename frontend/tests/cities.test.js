import { describe, expect, it } from 'vitest';
import { CITIES } from '../src/data/cities.js';

describe('catálogo de ciudades', () => {
  it('expone únicamente las ciudades definidas por la especificación', () => {
    expect(CITIES).toEqual([
      { label: 'Huánuco, Perú', value: 'Huanuco, Peru' },
      { label: 'Tingo María, Perú', value: 'Tingo Maria, Peru' },
    ]);
  });
});

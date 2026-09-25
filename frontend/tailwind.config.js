/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Los colores tematizados salen de las CSS custom properties definidas
      // en src/index.css. Asi se escribe `bg-bg text-text border-border` en los
      // componentes y el tema (claro/oscuro) se resuelve solo por CSS.
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        text: 'var(--color-text)',
        'text-muted': 'var(--color-text-muted)',
        border: 'var(--color-border)',
        primary: 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',
        'primary-text': 'var(--color-primary-text)',
        ring: 'var(--color-ring)',
        'error-text': 'var(--color-error-text)',
        'error-bg': 'var(--color-error-bg)',
        'error-border': 'var(--color-error-border)',
        'success-text': 'var(--color-success-text)',
        'success-bg': 'var(--color-success-bg)',
      },
    },
  },
  plugins: [],
};

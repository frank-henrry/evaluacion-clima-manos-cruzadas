# Práctica 1 — Frontend

Aplicación React para autenticación y consulta del clima por ciudad. Implementa
`specs/01-loginv2.md` y `specs/02-Consulta-clima.md`.

## Desarrollo

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

`VITE_API_URL` debe apuntar al backend (por defecto, `http://localhost:8000`).
El login usa `POST /auth/login`; no hay usuarios ni tokens simulados en el
cliente. Las credenciales válidas dependen de los usuarios registrados en el
backend.

Tras autenticarse se muestra un selector con Huánuco y Tingo María, ambas en
Perú. `Consultar` envía:

```http
GET /api/v1/weather?location={ciudad}
Authorization: Bearer {token}
```

La vista contempla carga, resultado, error recuperable y reintento. Si el
backend responde `401`, elimina la sesión en memoria y vuelve al login con un
aviso. Recargar la página también requiere iniciar sesión nuevamente; no se
persiste el JWT deliberadamente.

## Scripts

```bash
npm run test
npm run build
```

## Arquitectura

- `src/api`: acceso HTTP y traducción de errores a mensajes seguros.
- `src/hooks`: estado y coordinación de login/clima.
- `src/components`: containers y componentes presentacionales.
- `src/data/cities.js`: catálogo visible y valores canónicos para WeatherAPI.
- `src/validation`: reglas del formulario de login.

Los temas claro y oscuro usan variables CSS y `prefers-color-scheme`, sin una
librería de temas. La URL del backend se configura mediante entorno y la API
key de WeatherAPI permanece exclusivamente en el backend.

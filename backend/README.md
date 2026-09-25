# Practica 1 - API backend

API de login: `POST /auth/login` valida credenciales contra Postgres y devuelve
un JWT. Los usuarios autenticados pueden consultar el clima actual de una ciudad
mediante `GET /api/v1/weather`, integrado con WeatherAPI exclusivamente desde
el servidor. FastAPI + SQLAlchemy async + asyncpg + bcrypt + httpx.

## Estructura

```
backend/
  app/
    main.py              # FastAPI app, CORS, routers, lifespan
    api/
      auth.py            # router POST /auth/login (solo valida input y delega)
      health.py          # router GET /health
      weather.py         # router protegido GET /api/v1/weather
      dependencies.py    # autenticacion Bearer, validacion y dependencias
    services/
      auth_service.py    # logica: busca usuario, verifica bcrypt, emite JWT
      weather_service.py # transforma WeatherAPI al contrato publico
    integrations/
      weather_api.py     # cliente async de WeatherAPI
    models/
      schemas.py         # Pydantic: LoginRequest / LoginResponse
      weather.py         # modelos meteorologicos publicos y externos
    db/
      session.py         # engine + async_sessionmaker + get_session (dependencia)
      models.py          # modelo ORM User (tabla users)
      users.py           # query get_user_by_correo
    core/
      config.py          # Settings (pydantic-settings), lee env / .env
      security.py        # hash/verify bcrypt + create/decode JWT (HS256)
      exceptions.py      # AuthError (mensaje generico)
  seed.py                # siembra idempotente de usuarios de prueba
  requirements.txt
  .env.example
```

## Variables de entorno

| Variable             | Obligatoria | Default                                              | Descripcion |
|----------------------|-------------|-----------------------------------------------------|-------------|
| `DATABASE_URL`       | no          | `postgresql+asyncpg://practica:practica@localhost:5432/practica` | URL SQLAlchemy async (driver `asyncpg`). En Docker el host es `db`. |
| `JWT_SECRET`         | **si**      | (ninguno; la app no arranca sin el)                 | Secreto de firma HS256. Generar: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM`      | no          | `HS256`                                             | Algoritmo de firma. |
| `JWT_EXPIRE_MINUTES` | no          | `60`                                                | Minutos de validez del token (`exp`). |
| `CORS_ORIGINS`       | no          | `http://localhost:8080,http://localhost:5173`       | Origenes del frontend permitidos, separados por coma. |
| `WEATHER_API_KEY`    | para consultar clima | vacio                                      | Key privada de WeatherAPI. Si falta, el endpoint responde `503`; nunca se envia al frontend. |
| `WEATHER_API_BASE_URL` | no        | `https://api.weatherapi.com/v1`                     | URL base del proveedor. |
| `WEATHER_API_TIMEOUT_SECONDS` | no | `5`                                                 | Timeout total del cliente HTTP, en segundos. |

Copiar `.env.example` a `.env` y ajustar.

## Correr en local

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env        # y editar JWT_SECRET (y DATABASE_URL si hace falta)

# Con un Postgres corriendo en localhost:5432 y la db creada:
python seed.py              # crea la tabla users e inserta los usuarios de prueba

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Docs interactivas: http://localhost:8000/docs
- Health: http://localhost:8000/health

El frontend espera el backend en `http://localhost:8000` (`VITE_API_URL`).

## Contrato del endpoint

### `POST /auth/login`

Request (JSON):

```json
{ "correo": "admin@practica.com", "password": "admin123" }
```

- `correo`: email valido, sin espacios en blanco. Obligatorio.
- `password`: string no vacio. Obligatorio.

Respuesta `200`:

```json
{ "correo": "admin@practica.com", "token": "<JWT HS256>", "token_type": "bearer" }
```

Errores:

| Status | Cuando | Body |
|--------|--------|------|
| `422`  | Falta un campo, email mal formado, correo con espacios, password vacio | `{"detail": [ ... ]}` (Pydantic) |
| `401`  | Correo no registrado **o** contrasena incorrecta (mismo mensaje en ambos casos) | `{"detail": "Correo o contraseña incorrectos."}` |

### `GET /health`

`200` -> `{"status": "ok"}`

### `GET /api/v1/weather?location=Huanuco%2C%20Peru`

Requiere `Authorization: Bearer <JWT>` emitido por el login. `location` se
normaliza con `strip`, debe tener entre 1 y 100 caracteres y no puede contener
caracteres de control.

WeatherAPI recibe `q=<ciudad>` y `lang=es`. La respuesta publica utiliza el
nombre de ubicacion resuelto por el proveedor:

```json
{
  "location": "Huanuco",
  "temperature": "24°C",
  "condition": "Despejado",
  "humidity": "60%"
}
```

| Status | Cuando |
|--------|--------|
| `401` | JWT ausente, invalido o expirado |
| `404` | WeatherAPI no encuentra la ciudad |
| `422` | `location` falta o no supera la validacion |
| `502` | El proveedor devuelve un payload invalido |
| `503` | Falta configuracion, hay un error de red o el proveedor rechaza/no puede atender la solicitud |

Las respuestas de error son saneadas: no publican la key ni el detalle recibido
del proveedor.

## JWT

Emitido en `app/core/security.py:create_access_token`. Firma **HS256** con
`JWT_SECRET`. Claims:

```json
{ "sub": "<correo>", "correo": "<correo>", "iat": <epoch>, "exp": <epoch + JWT_EXPIRE_MINUTES*60> }
```

## Usuarios de prueba

Son usuarios sembrados para desarrollo; el frontend los valida mediante el
endpoint real `POST /auth/login`:

| correo                | password    |
|-----------------------|-------------|
| `admin@practica.com`  | `admin123`  |
| `jperez@practica.com` | `Practica-1`|

Se siembran de dos formas (elegir una):

1. **`db/init.sql`** (via principal en Docker): lo ejecuta el contenedor de
   Postgres al inicializarse con el volumen vacio. Trae los hashes bcrypt
   precalculados y `CREATE TABLE users`.
2. **`backend/seed.py`** (local / db ya inicializada): idempotente, crea la
   tabla si falta e inserta solo los que no existen. `python seed.py`.

## Pruebas

```bash
cd backend
pytest -q
```

Las pruebas meteorologicas usan un transporte HTTP simulado; no requieren red
ni una key real de WeatherAPI.

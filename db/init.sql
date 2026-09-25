-- Inicializacion de la base de datos de autenticacion (Practica 1).
--
-- VIA PRINCIPAL DE SEED (Docker): el contenedor oficial de Postgres ejecuta
-- automaticamente los .sql montados en /docker-entrypoint-initdb.d/ la primera
-- vez que arranca con el volumen de datos vacio.
--
-- Alternativa (entorno local ya inicializado, sin recrear el volumen):
--   cd backend && python seed.py     (idempotente)

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    correo        VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_correo ON users (correo);

-- Usuarios de prueba. Coinciden con MOCK_USERS de frontend/src/api/authApi.js:
--   admin@practica.com  / admin123
--   jperez@practica.com / Practica-1
-- password_hash = bcrypt (cost 12) precalculado. La contrasena en claro nunca
-- se almacena ni se loggea.
INSERT INTO users (correo, password_hash) VALUES
    ('admin@practica.com',  '$2b$12$uHf4LpUjZQCqbx4i5NRmZ.GeDrcTgr6GVAnmf39eRmVOy/u2SNMUO'),
    ('jperez@practica.com', '$2b$12$fcpPk0O/RSKKf.eZcUkqBerOfidBbcZX7xXJifF/Mrp5fDGUvSYjy')
ON CONFLICT (correo) DO NOTHING;

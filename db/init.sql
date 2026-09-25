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

-- Datos historicos de visitas (SPEC 03). Las filas se generan e insertan con:
--   cd backend && python seed_visitas.py     (idempotente)
CREATE TABLE IF NOT EXISTS lugar_turistico (
    id           BIGSERIAL PRIMARY KEY,
    codigo       VARCHAR(50)  NOT NULL UNIQUE,  -- "manos-cruzadas"
    nombre       VARCHAR(120) NOT NULL,         -- "Las Manos Cruzadas"
    sitio        VARCHAR(120) NOT NULL,         -- "Templo de Kotosh"
    ubicacion    VARCHAR(120) NOT NULL,         -- "Huánuco, Perú"
    horario      VARCHAR(60)  NOT NULL,         -- "08:00-17:00" (mock)
    aforo_maximo INTEGER      NOT NULL          -- 600 (mock)
);

CREATE TABLE IF NOT EXISTS visitas_historicas (
    id                 BIGSERIAL PRIMARY KEY,
    lugar_id           BIGINT       NOT NULL REFERENCES lugar_turistico(id),
    fecha              DATE         NOT NULL,
    dia_semana         VARCHAR(10)  NOT NULL, -- Lunes..Domingo
    condicion_clima    VARCHAR(25)  NOT NULL,
    temperatura_max    NUMERIC(4,1) NOT NULL,
    es_feriado         BOOLEAN      NOT NULL DEFAULT FALSE,
    temporada          VARCHAR(12)  NOT NULL, -- escolar | vacacional
    visitantes_totales INTEGER      NOT NULL CHECK (visitantes_totales >= 0),
    UNIQUE (lugar_id, fecha)
);

CREATE INDEX IF NOT EXISTS ix_visitas_similitud
    ON visitas_historicas (lugar_id, dia_semana, condicion_clima, es_feriado);

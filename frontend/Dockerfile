# syntax=docker/dockerfile:1

##############################################################################
# Stage 1 - build: compila los estaticos con Vite usando Node.
##############################################################################
FROM node:20-alpine AS build

WORKDIR /app

# Instalacion reproducible de dependencias (requiere package-lock.json).
# Se copia solo el manifiesto primero para aprovechar la cache de capas.
COPY package.json package-lock.json ./
RUN npm ci

# Codigo fuente y config de build (src/, index.html, vite/tailwind/postcss config).
COPY . .

# La URL del backend se inyecta en TIEMPO DE BUILD: Vite embebe las variables
# VITE_* dentro del bundle, no se pueden cambiar despues sin recompilar.
# No se hardcodea: llega como build-arg desde docker-compose / .env.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

##############################################################################
# Stage 2 - runtime: sirve los estaticos de dist/ con nginx.
##############################################################################
FROM nginx:alpine AS runtime

# Config de nginx pensada para SPA (fallback a index.html).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Solo los artefactos compilados pasan a la imagen final (sin node_modules ni fuentes).
COPY --from=build /app/dist /usr/share/nginx/html

# nginx escucha en HTTP plano en el puerto 80 dentro del contenedor.
# La terminacion TLS (si el entorno no es local) va delante de este contenedor.
EXPOSE 80

# Healthcheck simple: el index tiene que responder 200.
# Se usa 127.0.0.1 (no "localhost"): dentro del contenedor localhost resuelve a ::1
# y nginx escucha solo en IPv4, con lo que "localhost" daria connection refused.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

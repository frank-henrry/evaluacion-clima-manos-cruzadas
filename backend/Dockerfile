# syntax=docker/dockerfile:1

##############################################################################
# Backend - Practica 1: FastAPI + Uvicorn sobre python:3.11-slim.
# Una imagen = una responsabilidad (solo la API). La db va en su propio
# contenedor. Nada de secrets aca: JWT_SECRET / DATABASE_URL llegan por
# variable de entorno desde docker-compose / .env, nunca horneados en la imagen.
##############################################################################
FROM python:3.11-slim

# - No escribir .pyc, salida sin buffer (logs directos a docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Solo el manifiesto primero -> capa de deps cacheada mientras no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Luego el codigo de la app (cambia seguido, no invalida la capa de deps).
COPY . .

# Usuario no-root: la app corre sin privilegios dentro del contenedor.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Puerto interno de la API (se publica al host desde docker-compose).
EXPOSE 8000

# Healthcheck sin curl (no viene en slim): urllib de la stdlib.
# 127.0.0.1 explicito (no "localhost"): dentro del contenedor localhost puede
# resolver a ::1 y uvicorn escucha en IPv4, con lo que daria connection refused.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else sys.exit(1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

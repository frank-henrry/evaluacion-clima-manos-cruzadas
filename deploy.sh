#!/usr/bin/env bash
# Deploy a produccion: corre los tests del backend con umbral de cobertura
# (definido en backend/pytest.ini, --cov-fail-under=80) y SOLO si pasan
# levanta/reconstruye los contenedores con docker compose.
set -euo pipefail

cd "$(dirname "$0")"

echo "== Backend: tests + cobertura =="
cd backend
python3 -m venv .venv --clear >/dev/null 2>&1 || true
source .venv/bin/activate
pip install -q -r requirements.txt
python -m pytest
deactivate
cd ..

echo "== Cobertura OK. Desplegando contenedores =="
docker compose up --build -d

"""Configuracion comun de pruebas; no contiene credenciales reales."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-tests-only")

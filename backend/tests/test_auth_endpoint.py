"""Pruebas de POST /auth/login y GET /health sin Postgres real.

`get_session` se reemplaza por una sesion falsa cuyo `execute` devuelve el
usuario configurado; asi se ejercita tambien `app.db.users.get_user_by_correo`.
"""

import httpx
import pytest
import pytest_asyncio

from app.core.security import (
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.session import get_session
from app.main import app

MENSAJE_401 = {"detail": "Correo o contraseña incorrectos."}
CORREO = "admin@practica.com"
PASSWORD = "admin123"


class _FakeResult:
    def __init__(self, user: User | None) -> None:
        self._user = user

    def scalar_one_or_none(self) -> User | None:
        return self._user


class FakeSession:
    """Imita AsyncSession.execute: devuelve el usuario si el correo coincide."""

    def __init__(self, users: dict[str, User]) -> None:
        self.users = users
        self.correos_consultados: list[str] = []

    async def execute(self, statement):
        params = statement.compile().params
        correo = next(iter(params.values()))
        self.correos_consultados.append(correo)
        return _FakeResult(self.users.get(correo))


@pytest.fixture(scope="module")
def admin_user() -> User:
    return User(id=1, correo=CORREO, password_hash=hash_password(PASSWORD))


@pytest.fixture
def fake_session(admin_user: User):
    session = FakeSession({CORREO: admin_user})

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield session
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --------------------------------------------------------------------- 200


@pytest.mark.asyncio
async def test_login_ok_devuelve_contrato_y_jwt_valido(client, fake_session) -> None:
    response = await client.post(
        "/auth/login", json={"correo": CORREO, "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"correo", "token", "token_type"}
    assert body["correo"] == CORREO
    assert body["token_type"] == "bearer"
    assert "password_hash" not in response.text
    assert "password" not in body

    claims = decode_access_token(body["token"])
    assert claims["sub"] == CORREO
    assert claims["correo"] == CORREO
    assert claims["exp"] > claims["iat"]


@pytest.mark.asyncio
async def test_login_normaliza_correo_a_minusculas(client, fake_session) -> None:
    response = await client.post(
        "/auth/login", json={"correo": "ADMIN@Practica.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert fake_session.correos_consultados == [CORREO]
    assert response.json()["correo"] == CORREO
    assert decode_access_token(response.json()["token"])["sub"] == CORREO


# --------------------------------------------------------------------- 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("correo", "password"),
    [
        ("noexiste@practica.com", PASSWORD),  # correo inexistente
        (CORREO, "incorrecta"),  # contrasena incorrecta
        (CORREO, "ADMIN123"),  # contrasena sensible a mayusculas
    ],
    ids=["correo-inexistente", "password-incorrecta", "password-mayusculas"],
)
async def test_login_credenciales_invalidas_mismo_mensaje(
    client, fake_session, correo: str, password: str
) -> None:
    response = await client.post(
        "/auth/login", json={"correo": correo, "password": password}
    )

    assert response.status_code == 401
    assert response.json() == MENSAJE_401
    assert "token" not in response.text


@pytest.mark.asyncio
async def test_login_hash_corrupto_en_db_responde_401(client) -> None:
    session = FakeSession({CORREO: User(id=2, correo=CORREO, password_hash="no-es-bcrypt")})

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        response = await client.post(
            "/auth/login", json={"correo": CORREO, "password": PASSWORD}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == MENSAJE_401


# --------------------------------------------------------------------- 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "campo"),
    [
        ({"correo": " admin@practica.com", "password": PASSWORD}, "correo"),
        ({"correo": "admin @practica.com", "password": PASSWORD}, "correo"),
        ({"correo": "admin@practica.com ", "password": PASSWORD}, "correo"),
        ({"correo": "no-es-un-correo", "password": PASSWORD}, "correo"),
        ({"correo": "", "password": PASSWORD}, "correo"),
        ({"password": PASSWORD}, "correo"),
        ({"correo": CORREO}, "password"),
        ({"correo": CORREO, "password": ""}, "password"),
        ({"correo": CORREO, "password": "   "}, "password"),
    ],
    ids=[
        "correo-espacio-inicial",
        "correo-espacio-medio",
        "correo-espacio-final",
        "correo-invalido",
        "correo-vacio",
        "falta-correo",
        "falta-password",
        "password-vacio",
        "password-solo-espacios",
    ],
)
async def test_login_body_invalido_422(client, fake_session, payload, campo) -> None:
    response = await client.post("/auth/login", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(err["loc"] == ["body", campo] for err in detail)
    # Nunca llega a consultar la base de datos.
    assert fake_session.correos_consultados == []


@pytest.mark.asyncio
async def test_login_422_mensajes_del_contrato(client, fake_session) -> None:
    r_correo = await client.post(
        "/auth/login", json={"correo": " admin@practica.com", "password": PASSWORD}
    )
    r_password = await client.post(
        "/auth/login", json={"correo": CORREO, "password": "   "}
    )

    assert r_correo.json()["detail"][0]["msg"] == (
        "Value error, El correo no debe contener espacios en blanco."
    )
    assert r_password.json()["detail"][0]["msg"] == (
        "Value error, La contraseña es obligatoria."
    )


# ---------------------------------------------------------------- security


def test_hash_y_verify_password_roundtrip() -> None:
    hashed = hash_password(PASSWORD)

    assert hashed != PASSWORD
    assert hashed.startswith("$2")
    assert verify_password(PASSWORD, hashed) is True
    assert verify_password("otra", hashed) is False


def test_verify_password_con_hash_invalido_devuelve_false() -> None:
    assert verify_password(PASSWORD, "hash-invalido") is False


# ------------------------------------------------------------------ health


@pytest.mark.asyncio
async def test_health_ok(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

"""Router de autenticacion. Solo valida input (Pydantic) y delega al service."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.db.session import get_session
from app.models.schemas import LoginRequest, LoginResponse
from app.services.auth_service import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"description": "Correo o contraseña incorrectos."}},
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    try:
        result = await authenticate(session, payload.correo, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc

    return LoginResponse(correo=result.correo, token=result.token)

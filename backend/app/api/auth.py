from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.auth import (
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.api.deps import require_admin, require_customer
from app.core.idempotency import IdempotentRequest
from app.models.system import IdempotencyKey


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegisterRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    try:
        user = await service.register(data)
        return user
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLoginRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    try:
        user = await service.authenticate(data.email, data.password)
        return service.create_tokens(user)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh")
async def refresh_token(data: TokenRefreshRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    try:
        new_access = service.refresh_access_token(data.refresh_token)
        return {"access_token": new_access, "token_type": "bearer"}
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# 1. Route only ADMINS can access
@router.get("/admin-only")
async def admin_only_endpoint(admin: User = Depends(require_admin)):
    return {"message": f"Welcome Admin {admin.email}"}


# 2. Simulated billing action that requires Idempotency-Key
@router.post("/test-charge")
async def test_charge_endpoint(
    session: AsyncSession = Depends(get_db),
    idem_key: IdempotencyKey = Depends(IdempotentRequest(required=True)),
):
    # Simulate a successful charge
    idem_key.response_status = 200
    idem_key.response_body = {"status": "paid", "amount_paise": 149900}
    await session.commit()
    return idem_key.response_body
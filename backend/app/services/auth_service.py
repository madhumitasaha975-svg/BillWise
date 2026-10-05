from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Customer, User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserRegisterRequest


class AuthError(Exception):
    """Base exception for authentication failures."""
    pass


class EmailAlreadyExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(self, data: UserRegisterRequest) -> User:
        """Register a new customer user and initialize their customer profile."""
        existing = await self.users.get_by_email(data.email)
        if existing:
            raise EmailAlreadyExistsError("A user with this email already exists.")

        # 1. Create the user with hashed password
        hashed = hash_password(data.password)
        user = User(
            email=data.email,
            hashed_password=hashed,
            role=UserRole.CUSTOMER,
        )
        await self.users.add(user)

        # 2. Automatically create the associated customer billing profile
        customer = Customer(
            user_id=user.id,
            name=data.name,
        )
        await self.users.add_customer(customer)

        await self.session.commit()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        """Verify user credentials and return the user."""
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")
        return user

    def create_tokens(self, user: User) -> TokenResponse:
        """Generate access and refresh tokens for a user."""
        payload = {"sub": str(user.id), "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(payload),
            refresh_token=create_refresh_token(payload),
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Validate a refresh token and return a new access token."""
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError:
            raise InvalidTokenError("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Token is not a refresh token.")

        new_payload = {"sub": payload["sub"], "role": payload["role"]}
        return create_access_token(new_payload)
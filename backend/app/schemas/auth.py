from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import UserRole


# 1. Request payload when registering a new user
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: str = Field(..., min_length=1, max_length=100, description="Customer or organization name")


# 2. Request payload when logging in
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


# 3. Response payload when tokens are issued
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 4. Request payload when refreshing an access token
class TokenRefreshRequest(BaseModel):
    refresh_token: str


# 5. Safe public user representation (never exposes password hash!)
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
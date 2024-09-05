from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    email: EmailStr
    is_active: bool
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str

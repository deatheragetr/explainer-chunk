from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class EmailUpdate(BaseModel):
    email: EmailStr


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)


class VerifyEmailRequest(BaseModel):
    token: str

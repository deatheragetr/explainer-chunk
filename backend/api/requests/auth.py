from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)

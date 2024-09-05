from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    email: EmailStr
    is_active: bool
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class GeoLocation(BaseModel):
    country: str
    city: str
    latitude: Optional[float]
    longitude: Optional[float]


class SessionResponse(BaseModel):
    ip: str
    user_agent: str
    geolocation: GeoLocation
    created_at: datetime

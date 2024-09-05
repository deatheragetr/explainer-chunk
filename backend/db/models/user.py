from bson import ObjectId
from datetime import datetime
from typing import TypedDict, Annotated
from pydantic import EmailStr


class MongoUser(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    email: Annotated[EmailStr, "User Email"]
    hashed_password: Annotated[str, "Bcrypt hashed password"]
    is_active: Annotated[bool, "Whether the user account is active"]
    is_verified: Annotated[bool, "Whether the user's email is verified"]
    created_at: Annotated[datetime, "Timestamp of user creation"]
    updated_at: Annotated[datetime, "Timestamp of last user update"]

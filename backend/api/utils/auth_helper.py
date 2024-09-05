from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr
from config.mongo import get_db, TypedAsyncIOMotorDatabase, AsyncIOMotorCollection
from config.environment import CryptoSettings
from db.models.user import MongoUser


# Password hashing
pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 setup
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="token")


crypto_settings = CryptoSettings()
SECRET_KEY = crypto_settings.secret_key
ALGORITHM = crypto_settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = crypto_settings.access_token_expiration_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def get_user(
    email: EmailStr, db: TypedAsyncIOMotorDatabase
) -> Optional[MongoUser]:
    users_collection: AsyncIOMotorCollection[MongoUser] = db.users
    user = await users_collection.find_one({"email": email})
    return user


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode: Dict[str, Any] = data.copy()
    if expires_delta:
        expire: datetime = datetime.now(datetime.UTC) + expires_delta
    else:
        expire: datetime = datetime.now(datetime.UTC) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(
    email: EmailStr, password: str, db: TypedAsyncIOMotorDatabase
) -> Union[MongoUser, bool]:
    user: Optional[MongoUser] = await get_user(email, db)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: TypedAsyncIOMotorDatabase = Depends(get_db)
) -> MongoUser:
    credentials_exception: HTTPException = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: Dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user: Optional[MongoUser] = await get_user(email, db)
    if user is None:
        raise credentials_exception
    return user

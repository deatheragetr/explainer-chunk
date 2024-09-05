from datetime import timedelta
import datetime
from typing import Optional, Dict, Any, Union, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr
from config.mongo import get_db, TypedAsyncIOMotorDatabase, AsyncIOMotorCollection
from config.environment import CryptoSettings, DataSettings
from db.models.user import MongoUser
from config.redis import redis_pool, RedisType
import uuid
import geoip2.database

# Password hashing
pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 setup
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="token")

crypto_settings = CryptoSettings()
SECRET_KEY = crypto_settings.secret_key
ALGORITHM = crypto_settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = crypto_settings.access_token_expiration_minutes
REFRESH_TOKEN_EXPIRATION_DAYS = crypto_settings.refresh_token_expiration_days
data_settings = DataSettings()

# GeoIP database
geoip_reader = geoip2.database.Reader(data_settings.path_to_geoip_db)


async def get_redis_client() -> RedisType:
    return await redis_pool.get_client()


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


def create_token(
    data: Dict[str, Any], expires_delta: timedelta, token_type: str
) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_access_token(data: Dict[str, Any]) -> str:
    return create_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(data: Dict[str, Any]) -> str:
    return create_token(data, timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS), "refresh")


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
    token: str = Depends(oauth2_scheme),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
) -> MongoUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub", "")
        if email is "":
            raise credentials_exception
        token_type: str = payload.get("type", "")
        if token_type != "access":
            raise credentials_exception

        # Check if token is blacklisted
        is_blacklisted = await redis.sismember(f"blacklisted_tokens", token)
        if is_blacklisted:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user(email, db)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_refresh_token(
    token: str = Depends(oauth2_scheme),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
) -> MongoUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub", "")
        if email is "":
            raise credentials_exception
        token_type: str = payload.get("type", "")
        if token_type != "refresh":
            raise credentials_exception

        # Check if refresh token is valid
        is_valid = await redis.sismember(f"user_refresh_tokens:{email}", token)
        if not is_valid:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user(email, db)
    if user is None:
        raise credentials_exception
    return user


def get_client_ip(request: Request) -> str:
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host


def get_geolocation(ip: str) -> Dict[str, Any]:
    try:
        response = geoip_reader.city(ip)
        return {
            "country": response.country.name,
            "city": response.city.name,
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
        }
    except:
        return {
            "country": "Unknown",
            "city": "Unknown",
            "latitude": None,
            "longitude": None,
        }


async def add_user_session(
    email: str, refresh_token: str, ip: str, user_agent: str, redis: RedisType
) -> None:
    session_id = str(uuid.uuid4())
    geolocation = get_geolocation(ip)
    session_data = {
        "refresh_token": refresh_token,
        "ip": ip,
        "user_agent": user_agent,
        "geolocation": geolocation,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    await redis.hset(f"user_sessions:{email}", session_id, str(session_data))
    await redis.sadd(f"user_refresh_tokens:{email}", refresh_token)
    await redis.expire(
        f"user_sessions:{email}", REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60
    )
    await redis.expire(
        f"user_refresh_tokens:{email}", REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60
    )


async def get_user_sessions(email: str, redis: RedisType) -> List[Dict[str, Any]]:
    sessions = await redis.hgetall(f"user_sessions:{email}")
    return [eval(session) for session in sessions.values()]


async def remove_user_session(email: str, refresh_token: str, redis: RedisType) -> None:
    sessions = await redis.hgetall(f"user_sessions:{email}")
    for session_id, session_data in sessions.items():
        if eval(session_data)["refresh_token"] == refresh_token:
            await redis.hdel(f"user_sessions:{email}", session_id)
            break
    await redis.srem(f"user_refresh_tokens:{email}", refresh_token)


async def blacklist_token(token: str, redis: RedisType) -> None:
    await redis.sadd("blacklisted_tokens", token)
    # Set expiration for blacklisted token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = payload.get("exp")
    if exp:
        ttl = max(exp - int(datetime.datetime.now(datetime.UTC).timestamp()), 0)
        await redis.expire("blacklisted_tokens", ttl)

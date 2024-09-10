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
    access_token: str = Depends(oauth2_scheme),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
) -> MongoUser:
    """
    Authenticate and retrieve the current user using an access token.

    This function is used for regular API authentication using access tokens,
    as opposed to 'get_current_user_refresh_token' which uses refresh tokens.
    The key differences are:

    1. Token source: This function uses the oauth2_scheme to extract the token
       from the Authorization header, typically in the format "Bearer <token>".
    2. Token type: It expects and validates an access token, which has a shorter
       lifespan and is used for authenticating API requests.
    3. Use case: This is used for most authenticated API endpoints to verify
       the user's identity and permissions.

    The oauth2_scheme is a FastAPI dependency that extracts the token from
    the Authorization header. It returns a string containing the raw JWT token.

    Args:
        token (str): The access token extracted by oauth2_scheme.
        db (TypedAsyncIOMotorDatabase): The database connection.
        redis (RedisType): The Redis connection for token blacklist checking.

    Returns:
        MongoUser: The authenticated user's data.

    Raises:
        HTTPException: If the token is invalid, expired, or the user doesn't exist.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},
        )
        email: str = payload.get("sub", "")
        if email is "":
            raise credentials_exception
        token_type: str = payload.get("type", "")
        if token_type != "access":
            raise credentials_exception

        # Check if token is blacklisted
        is_blacklisted = await redis.sismember(f"blacklisted_tokens", access_token)
        if is_blacklisted:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user(email, db)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_refresh_token(
    request: Request,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
) -> MongoUser:
    """
    Authenticate and retrieve the current user using a refresh token.

    This function is specifically designed for refresh token authentication,
    as opposed to the regular 'get_current_user' function which uses access tokens.
    It's used in the token refresh process to issue new access tokens without
    requiring the user to re-enter their credentials.

    The function performs the following steps:
    1. Retrieves the refresh token from the request's cookies.
    2. Decodes and validates the refresh token.
    3. Checks if the refresh token is still valid in Redis.
    4. Retrieves and returns the user associated with the token.

    Args:
        request (Request): The FastAPI request object.
        db (TypedAsyncIOMotorDatabase): The database dependency.
        redis (RedisType): The Redis client dependency.

    Returns:
        MongoUser: The authenticated user.

    Raises:
        HTTPException: If the refresh token is invalid, expired, or the user doesn't exist.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise credentials_exception
    try:
        payload = jwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},
        )
        email: str = payload.get("sub", "")
        if email is "":
            raise credentials_exception
        token_type: str = payload.get("type", "")
        if token_type != "refresh":
            raise credentials_exception

        # Check if refresh token is valid
        is_valid = await redis.sismember(f"user_refresh_tokens:{email}", refresh_token)
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
    """
    Add a new user session and refresh token to Redis.

    This function creates a new session for a user and stores it in Redis. It also adds
    the refresh token to a separate set in Redis.

    User sessions and refresh tokens are related but serve different purposes:
    - User sessions: Contain detailed information about each active session, including
      IP, user agent, geolocation, and creation time. They allow for tracking and
      managing individual login instances.
    - User refresh tokens: A set of valid refresh tokens for the user. This allows for
      quick validation of refresh tokens without needing to check the full session data.

    Both user sessions and refresh tokens are set to expire after REFRESH_TOKEN_EXPIRATION_DAYS.
    This automatic expiration helps in maintaining clean data and enforcing token lifetimes.

    Args:
        email (str): The user's email address.
        refresh_token (str): The refresh token for the session.
        ip (str): The IP address of the client.
        user_agent (str): The user agent string of the client.
        redis (RedisType): The Redis client instance.

    Returns:
        None
    """
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


async def blacklist_token(access_token: str, redis: RedisType) -> None:
    await redis.sadd("blacklisted_tokens", access_token)
    # Set expiration for blacklisted token
    payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = payload.get("exp")
    if exp:
        ttl = max(exp - int(datetime.datetime.now(datetime.UTC).timestamp()), 0)
        await redis.expire("blacklisted_tokens", ttl)

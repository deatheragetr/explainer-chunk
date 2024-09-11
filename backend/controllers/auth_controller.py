from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    BackgroundTasks,
)
from fastapi.security import OAuth2PasswordRequestForm
import datetime
from jose import jwt, JWTError

from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from typing import List
from config.mongo import get_db, TypedAsyncIOMotorDatabase
from db.models.user import MongoUser
from config.redis import RedisType
from config.environment import AppSettings, CryptoSettings
from background.huey_jobs.post_user_registration_job import post_registration_job

from api.utils.auth_helper import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    get_current_user,
    get_current_user_refresh_token,
    get_client_ip,
    add_user_session,
    get_user_sessions,
    remove_user_session,
    blacklist_token,
    get_redis_client,
    verify_password,
    REFRESH_TOKEN_EXPIRATION_DAYS,
)
from utils.email_utils import (
    create_verification_token,
    send_email_change_verification,
)

from api.requests.auth import UserCreate, UserUpdate, PasswordChange, VerifyEmailRequest
from api.responses.auth import UserResponse, TokenResponse, SessionResponse

router = APIRouter()
app_settings = AppSettings()
crypto_settings = CryptoSettings()


@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
    request: Request,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    _: str = Depends(RateLimiter(times=5, seconds=60)),
):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(user.password)
    new_user: MongoUser = {
        "_id": ObjectId(),
        "email": user.email,
        "hashed_password": hashed_password,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.datetime.now(datetime.UTC),
        "updated_at": datetime.datetime.now(datetime.UTC),
    }

    result = await db.users.insert_one(new_user)
    created_user = await db.users.find_one({"_id": result.inserted_id})

    post_registration_job(user_id=result.inserted_id)

    return UserResponse(
        email=created_user["email"],
        is_active=created_user["is_active"],
        is_verified=created_user["is_verified"],
    )


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest, db: TypedAsyncIOMotorDatabase = Depends(get_db)
):
    try:
        payload = jwt.decode(
            request.token, crypto_settings.secret_key, algorithms=["HS256"]
        )
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user["is_verified"]:
        return {"message": "Email already verified"}

    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "is_verified": True,
                "updated_at": datetime.datetime.now(datetime.UTC),
            }
        },
    )

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
    _: str = Depends(RateLimiter(times=10, seconds=60)),
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["email"]})
    refresh_token = create_refresh_token(data={"sub": user["email"]})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Use only with HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60,
        path="/auth/refresh",  # Restrict to refresh endpoint
    )

    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    await add_user_session(user["email"], refresh_token, ip, user_agent, redis)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            email=user["email"],
            is_active=user["is_active"],
            is_verified=user["is_verified"],
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    current_user: MongoUser = Depends(get_current_user_refresh_token),
    redis: RedisType = Depends(get_redis_client),
):
    old_refresh_token = request.cookies.get("refresh_token")
    if not old_refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token missing")

    await remove_user_session(current_user["email"], old_refresh_token, redis)

    access_token = create_access_token(data={"sub": current_user["email"]})
    refresh_token = create_refresh_token(data={"sub": current_user["email"]})

    # Set new refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60,
        path="/auth/refresh",
    )

    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    await add_user_session(current_user["email"], refresh_token, ip, user_agent, redis)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            email=current_user["email"],
            is_active=current_user["is_active"],
            is_verified=current_user["is_verified"],
        ),
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: MongoUser = Depends(get_current_user),
    access_token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
    redis: RedisType = Depends(get_redis_client),
):
    await blacklist_token(access_token, redis)
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await remove_user_session(current_user["email"], refresh_token, redis)

    response.delete_cookie(key="refresh_token", path="/auth/refresh")
    return {"message": "Successfully logged out"}


@router.get("/users/me", response_model=UserResponse)
async def read_users_me(
    current_user: MongoUser = Depends(get_current_user),
    _: str = Depends(RateLimiter(times=30, seconds=60)),
):
    return UserResponse(
        email=current_user["email"],
        is_active=current_user["is_active"],
        is_verified=current_user["is_verified"],
    )


@router.put("/users/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: MongoUser = Depends(get_current_user),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    _: str = Depends(RateLimiter(times=5, seconds=60)),
):
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    if "email" in update_data and update_data["email"] != current_user["email"]:
        # Check if the new email is already in use
        existing_user = await db.users.find_one({"email": update_data["email"]})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

        # Set is_verified to False for the new email
        update_data["is_verified"] = False

        # Generate verification token and send email
        verification_token = create_verification_token(update_data["email"])
        verification_url = f"{request.base_url}verify-email?token={verification_token}"
        background_tasks.add_task(
            send_email_change_verification, update_data["email"], verification_url
        )

    if update_data:
        update_data["updated_at"] = datetime.datetime.now(datetime.UTC)
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": update_data})

    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    return UserResponse(
        email=updated_user["email"],
        is_active=updated_user["is_active"],
        is_verified=updated_user["is_verified"],
    )


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    password_change: PasswordChange,
    request: Request,
    current_user: MongoUser = Depends(get_current_user),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    redis: RedisType = Depends(get_redis_client),
):
    if not verify_password(
        password_change.current_password, current_user["hashed_password"]
    ):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    hashed_password = get_password_hash(password_change.new_password)

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "hashed_password": hashed_password,
                "updated_at": datetime.datetime.now(datetime.UTC),
            }
        },
    )

    # Invalidate all existing refresh tokens
    await redis.delete(f"user_refresh_tokens:{current_user['email']}")
    await redis.delete(f"user_sessions:{current_user['email']}")

    # Create new tokens
    access_token = create_access_token(data={"sub": current_user["email"]})
    refresh_token = create_refresh_token(data={"sub": current_user["email"]})

    # Add new session
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    await add_user_session(current_user["email"], refresh_token, ip, user_agent, redis)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            email=current_user["email"],
            is_active=current_user["is_active"],
            is_verified=current_user["is_verified"],
        ),
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_active_sessions(
    current_user: MongoUser = Depends(get_current_user),
    redis: RedisType = Depends(get_redis_client),
):
    sessions = await get_user_sessions(current_user["email"], redis)
    return [SessionResponse(**session) for session in sessions]


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: MongoUser = Depends(get_current_user),
    redis: RedisType = Depends(get_redis_client),
):
    await redis.delete(f"user_refresh_tokens:{current_user['email']}")
    await redis.delete(f"user_sessions:{current_user['email']}")
    return {"message": "Successfully logged out from all sessions"}

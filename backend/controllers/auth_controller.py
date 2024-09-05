from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import datetime
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from typing import List

from config.mongo import get_db, TypedAsyncIOMotorDatabase
from db.models.user import MongoUser
from config.redis import RedisType

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
)

from api.requests.auth import UserCreate, UserUpdate, PasswordChange
from api.responses.auth import UserResponse, TokenResponse, SessionResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
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

    return UserResponse(
        email=created_user["email"],
        is_active=created_user["is_active"],
        is_verified=created_user["is_verified"],
    )


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
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

    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    await add_user_session(user["email"], refresh_token, ip, user_agent, redis)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    current_user: MongoUser = Depends(get_current_user_refresh_token),
    redis: RedisType = Depends(get_redis_client),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
):
    await remove_user_session(current_user["email"], token, redis)

    access_token = create_access_token(data={"sub": current_user["email"]})
    refresh_token = create_refresh_token(data={"sub": current_user["email"]})

    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    await add_user_session(current_user["email"], refresh_token, ip, user_agent, redis)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    current_user: MongoUser = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
    redis: RedisType = Depends(get_redis_client),
):
    await blacklist_token(token, redis)
    await remove_user_session(current_user["email"], token, redis)
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
    current_user: MongoUser = Depends(get_current_user),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    _: str = Depends(RateLimiter(times=5, seconds=60)),
):
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

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

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


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

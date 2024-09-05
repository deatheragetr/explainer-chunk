from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from fastapi_limiter.depends import RateLimiter


from config.mongo import get_db, TypedAsyncIOMotorDatabase
from db.models.user import MongoUser

from api.utils.auth_helper import (
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

from api.requests.auth import UserCreate, UserUpdate
from api.responses.auth import UserResponse, TokenResponse

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
        "created_at": datetime.now(datetime.UTC),
        "updated_at": datetime.now(datetime.UTC),
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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    _: str = Depends(RateLimiter(times=10, seconds=60)),
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


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
        update_data["updated_at"] = datetime.now(datetime.UTC)
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": update_data})

    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    return UserResponse(
        email=updated_user["email"],
        is_active=updated_user["is_active"],
        is_verified=updated_user["is_verified"],
    )

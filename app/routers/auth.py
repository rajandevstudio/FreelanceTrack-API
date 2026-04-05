from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.helpers.user_helpers import get_user_by_email
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserRegister, UserResponse
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

# -----------------------------------------------------------------------------
# WHAT IS A ROUTER?
#
# In Django you had urls.py mapping URLs to views.
# In FastAPI, APIRouter groups related endpoints together.
# Each router has a prefix — so every route inside this file automatically
# starts with "/auth". You don't repeat it on every endpoint.
#
# tags=["auth"] groups these endpoints together in the Swagger UI docs.
# When you open /docs you'll see an "auth" section — clean and organised.
# -----------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,  # Pydantic filters the response through this schema
    status_code=status.HTTP_201_CREATED,  # 201 = Created (more correct than 200 for new resources)
)
async def register(
    payload: UserRegister,  # Pydantic validates the request body automatically
    db: AsyncSession = Depends(get_db),  # FastAPI injects the DB session
) -> UserResponse:
    """
    Register a new user account.

    Pydantic validates the request body BEFORE this function runs.
    If email is invalid, password too short, etc. — FastAPI returns 422
    automatically. Your code here only runs with clean, validated data.
    """

    # Check if email already exists
    # We do this BEFORE hashing the password — no point doing expensive
    # bcrypt work if we're just going to reject the request anyway
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create the user model instance
    # Notice: we never touch payload.password directly after this point
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),  # hash immediately
        hourly_rate=payload.hourly_rate,
    )

    db.add(new_user)
    await db.flush()  # sends INSERT to DB but doesn't commit yet
    # `flush` gives us the generated UUID back on new_user.id
    # without fully committing the transaction
    # get_db() in database.py commits after the route finishes

    return new_user  # Pydantic converts this ORM object → UserResponse JSON


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: UserRegister, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Login and receive a JWT access token.

    We use the same 'Invalid credentials' message whether the email
    doesn't exist OR the password is wrong. Never tell the client which
    one failed — that helps attackers enumerate valid emails.
    """

    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )

    # Step 1: Does this user exist?
    user = await get_user_by_email(db, payload.email)
    if not user:
        raise invalid_credentials_exception

    # Step 2: Is the password correct?
    # verify_password handles the bcrypt comparison — never do == on passwords
    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials_exception

    # Step 3: Is the account active?
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Step 4: Create and return JWT
    # "sub" is the JWT standard claim for "subject" — who this token belongs to
    token = create_access_token(data={"sub": user.email})

    return TokenResponse(access_token=token)

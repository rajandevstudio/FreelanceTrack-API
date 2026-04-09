from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.helpers.user_helpers import get_user_by_email
from app.models.user import User
from app.services.auth_service import decode_access_token

# -----------------------------------------------------------------------------
# WHAT IS A FASTAPI DEPENDENCY?
#
# A dependency is a function FastAPI calls automatically before your route runs.
# You declare it with `Depends()` in your route signature.
#
# Example:
#   @router.get("/projects")
#   async def get_projects(current_user: User = Depends(get_current_user)):
#       ...
#
# FastAPI sees `Depends(get_current_user)`, runs `get_current_user` first,
# and injects the result as `current_user`. If `get_current_user` raises
# an HTTPException, the route never runs — FastAPI returns the error immediately.
#
# This is powerful because:
#   - Auth logic lives in ONE place, not copy-pasted in every route
#   - Adding auth to a route = one line: `Depends(get_current_user)`
#   - Removing auth = remove that line. No other changes needed.
#   - Testable independently from routes
#
# This is similar to Django's @login_required decorator, but more flexible
# because dependencies can be chained, have their own dependencies, etc.
# -----------------------------------------------------------------------------

# OAuth2PasswordBearer tells FastAPI:
#   "Tokens come from the Authorization header as Bearer tokens"
#   "If no token, redirect the client to /api/v1/auth/login to get one"
# It also makes the Swagger UI show an Authorize button automatically.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),  # FastAPI extracts token from header
    db: AsyncSession = Depends(get_db),   # FastAPI gives us a DB session
) -> User:
    """
    Dependency that:
    1. Extracts JWT from Authorization header
    2. Decodes it to get the user's email
    3. Fetches the user from DB
    4. Returns the User object — or raises 401 if anything fails

    Any route that uses Depends(get_current_user) is automatically protected.
    No token = 401. Expired token = 401. Invalid token = 401.
    """

    # Single reusable exception — we use the same error for all failure cases
    # intentionally. We don't tell the client WHY it failed (expired vs invalid)
    # because that information helps attackers.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},  # OAuth2 standard header
    )

    # Step 1: Decode the token → get email
    email = decode_access_token(token)
    if email is None:
        raise credentials_exception

    # Step 2: Fetch user from DB
    user = await get_user_by_email(db, email)

    if user is None:
        raise credentials_exception

    # Step 3: Check account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user  # injected into the route as `current_user`
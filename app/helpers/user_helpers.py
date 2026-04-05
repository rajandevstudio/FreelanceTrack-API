from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


# -----------------------------------------------------------------------------
# WHY A HELPERS FILE?
#
# Common DB queries like "get user by email" will be needed in multiple places:
#   - auth dependency (to verify who's logged in)
#   - auth router (to check if email already exists on register)
#   - maybe admin routes later
#
# Instead of writing the same select() query in 3 different places,
# we write it once here and import it wherever needed.
# This is the DRY principle — Don't Repeat Yourself.
# -----------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Fetch a user by email. Returns None if not found or soft-deleted.
    `scalar_one_or_none()` returns the object or None — never raises an error
    if the row doesn't exist (unlike `scalar_one()` which raises if missing).
    """
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id) -> User | None:
    """Fetch a user by their UUID primary key."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted == False,
        )
    )
    return result.scalar_one_or_none()
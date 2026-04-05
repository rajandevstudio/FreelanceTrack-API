from pydantic import EmailStr, Field, field_validator

from app.schemas.base import AppBaseSchema, TimestampSchema


# -----------------------------------------------------------------------------
# THE SCHEMA PATTERN — one model, multiple schemas
#
# For a single User, we need FOUR different schemas:
#
#   UserRegister   → what the client sends when signing up
#   UserLogin      → what the client sends when logging in
#   UserResponse   → what we send BACK (never includes password)
#   UserUpdate     → what the client sends to update their profile
#
# This separation is important. If we used one schema for everything:
#   - we'd expose hashed_password in responses (security bug)
#   - we'd allow updating email in places we don't want
#   - Validation rules would conflict (password required on register, not on update)
#
# Each schema has EXACTLY the fields it needs — nothing more, nothing less.
# -----------------------------------------------------------------------------


class UserRegister(AppBaseSchema):
    """
    Validated when a new user signs up.
    `EmailStr` is a Pydantic type that validates email format automatically.
    No need to write regex — Pydantic handles it.
    """
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    hourly_rate: float = Field(default=0.0, ge=0)  # ge=0 means >= 0, no negative rates

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        """
        `Field(min_length=2)` catches empty strings, but "  " (spaces) would pass.
        This validator strips whitespace and re-checks.
        Validators run AFTER the field type is confirmed — so `v` is always a str here.
        """
        if not v.strip():
            raise ValueError("Full name cannot be blank or whitespace")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Basic password rules. In production we'd use a library like `zxcvbn`
        for proper strength checking, but this covers the basics.
        """
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLogin(AppBaseSchema):
    """
    Only email + password. Nothing else needed for login.
    Keeping schemas minimal means less data transferred and less attack surface.
    """
    email: EmailStr
    password: str


class UserResponse(TimestampSchema):
    """
    What we return to the client after register, login, or profile fetch.

    Notice what's NOT here:
    - hashed_password ← never expose this
    - deleted         ← internal field
    - is_active       ← internal field (we just return 401 if inactive)

    TimestampSchema gives us id, created_at, updated_at for free.
    """
    email: str
    full_name: str
    hourly_rate: float


class UserUpdate(AppBaseSchema):
    """
    For updating profile. All fields are Optional — the client can update
    just their name without touching hourly_rate, or vice versa.

    `None` as default means "not provided" — only provided fields get updated.
    This is called a PATCH pattern (partial update), as opposed to PUT (full replace).
    """
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    hourly_rate: float | None = Field(default=None, ge=0)


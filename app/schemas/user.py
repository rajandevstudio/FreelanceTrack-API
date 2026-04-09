from typing import Any
from urllib.parse import parse_qs

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.base import AppBaseSchema, TimestampSchema

from zxcvbn import zxcvbn 

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
    password: str = Field(min_length=8, max_length=72)  # bcrypt truncates to 72 chars, so we enforce that limit here
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
        Use zxcvbn for password strength estimation.
        Require a minimum score of 3 (strong) to prevent weak passwords.
        """
        result = zxcvbn(v)
        if result['score'] < 3:
            feedback = result.get('feedback', {})
            suggestions = feedback.get('suggestions', [])
            warning = feedback.get('warning', '')
            error_msg = "Password is too weak."
            if warning:
                error_msg += f" Warning: {warning}."
            if suggestions:
                error_msg += f" Suggestions: {' '.join(suggestions)}."
            raise ValueError(error_msg)
        return v


class UserLogin(AppBaseSchema):
    """
    Only email + password. Nothing else needed for login.
    Keeping schemas minimal means less data transferred and less attack surface.
    """
    email: EmailStr
    password: str

    @model_validator(mode="before")
    @classmethod
    def handle_username_as_email(cls, data: Any):
        if isinstance(data, dict):
            # If email not provided but username exists → map it
            if "email" not in data and "username" in data:
                data["email"] = data["username"]
        else:
            parsed = parse_qs(data.decode())
            # flatten values (parse_qs returns list values)
            data_ = {k: v[0] for k, v in parsed.items()}
            if "email" not in data_ and "username" in data_:
                data_["email"] = data_["username"]
            data = data_
        return data


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


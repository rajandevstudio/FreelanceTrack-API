import base64
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext


from app.config import settings

# -----------------------------------------------------------------------------
# PASSWORD HASHING
#
# `CryptContext` is from passlib — it handles hashing algorithms for us.
# We use bcrypt because:
#   1. It's intentionally slow (configurable "rounds") — brute force takes years
#   2. It automatically salts the hash — same password gives different hash each time
#   3. Industry standard — used by Django, Laravel, Rails, etc.
#
# NEVER do this: store plain passwords, use md5/sha1, or write your own hashing.
#
# How it works:
#   hash_password("mypassword123") → "$2b$12$abc...xyz" (60 char string)
#   verify_password("mypassword123", "$2b$12$abc...xyz") → True
#   verify_password("wrongpassword", "$2b$12$abc...xyz") → False
# -----------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(password, hashed_password)
    except Exception:
        return False

# -----------------------------------------------------------------------------
# JWT TOKENS
#
# JWT = JSON Web Token. It's a self-contained token that proves identity.
# Structure: header.payload.signature (three base64 parts separated by dots)
#
# Example decoded payload:
#   {
#     "sub": "rajan@example.com",   ← subject (who this token belongs to)
#     "exp": 1712345678             ← expiry timestamp (Unix time)
#   }
#
# The signature is created using SECRET_KEY — only your server can create
# valid tokens. If someone tampers with the payload, the signature breaks
# and verification fails.
#
# Flow:
#   1. User logs in with email + password
#   2. We verify password → correct → create JWT with their email inside
#   3. We return the JWT to the client
#   4. Client stores it (localStorage or memory) and sends it with every request:
#      Authorization: Bearer <token>
#   5. We decode the token on every request to know who's asking
#
# WHY JWT over sessions?
#   Sessions store state on the server (DB or Redis lookup per request).
#   JWTs are stateless — the token itself contains the info, no DB lookup needed.
#   This is why JWT is preferred for APIs and microservices.
# -----------------------------------------------------------------------------

def create_access_token(data: dict) -> str:
    """
    Creates a signed JWT token.

    `data` should contain {"sub": user_email}.
    We add expiry automatically based on settings.
    """
    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload["exp"] = expire  # JWT standard claim for expiry

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> str | None:
    """
    Decodes a JWT and returns the email (subject) inside it.
    Returns None if the token is invalid or expired.

    We catch JWTError broadly — whether it's expired, tampered,
    or malformed, the result is the same: we reject the request.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email: str | None = payload.get("sub")
        return email
    except JWTError:
        return None
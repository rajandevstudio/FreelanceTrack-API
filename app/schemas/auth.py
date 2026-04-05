from app.schemas.base import AppBaseSchema


# -----------------------------------------------------------------------------
# WHY A SEPARATE AUTH SCHEMA?
#
# When a user logs in successfully, we return a JWT token — not the user object.
# The client stores this token and sends it with every future request in the
# Authorization header: `Authorization: Bearer <token>`
#
# TokenResponse is simple — just the token string and its type.
# `token_type: "bearer"` is the OAuth2 standard. Always "bearer" for JWTs.
# -----------------------------------------------------------------------------


class TokenResponse(AppBaseSchema):
    access_token: str
    token_type: str = "bearer"


class TokenData(AppBaseSchema):
    """
    What we decode FROM the JWT token when verifying a request.
    We embed the user's email in the token payload when creating it,
    then read it back here to identify who is making the request.
    """
    email: str | None = None


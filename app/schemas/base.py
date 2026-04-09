import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# -----------------------------------------------------------------------------
# WHY A SHARED BASE SCHEMA?
#
# Same idea as MyModelMixin in models — define common config once.
#
# The most important setting here is `from_attributes=True`.
# This tells Pydantic: "you may receive a SQLAlchemy ORM object, not just
# a plain dict — read attributes from it directly."
#
# Without this, doing `UserResponse.model_validate(user_orm_object)` fails
# because Pydantic expects a dict, not an ORM object.
#
# In old Pydantic v1 this was called `orm_mode = True`.
# In Pydantic v2 it's `from_attributes = True` inside ConfigDict.
# -----------------------------------------------------------------------------


class AppBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(AppBaseSchema):
    """
    Adds id, created_at, updated_at to any response schema that needs them.
    We don't expose `deleted` — that's an internal field, not for API consumers.
    """
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class HealthResponse(BaseModel):
    status: str
    version: str
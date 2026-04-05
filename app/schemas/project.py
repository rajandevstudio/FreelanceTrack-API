import uuid

from pydantic import Field

from app.models.project import ProjectStatus
from app.schemas.base import AppBaseSchema, TimestampSchema


class ProjectCreate(AppBaseSchema):
    """
    What the client sends to create a new project.
    owner_id is NOT here — we get that from the logged-in user's JWT token.
    Never trust the client to tell you who owns something.
    """
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    client_name: str | None = Field(default=None, max_length=255)
    hourly_rate: float = Field(ge=0)
    budget: float | None = Field(default=None, ge=0)


class ProjectUpdate(AppBaseSchema):
    """
    All fields optional — supports partial updates (PATCH).
    A client can update just the status without resending everything.
    """
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    client_name: str | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    budget: float | None = Field(default=None, ge=0)
    status: ProjectStatus | None = None


class ProjectResponse(TimestampSchema):
    """
    Full project data returned to the client.

    `total_hours` and `total_earned` are computed properties on the model.
    Pydantic reads them just like regular fields because `from_attributes=True`
    in our base schema — it calls the @property getters automatically.
    """
    name: str
    description: str | None
    client_name: str | None
    hourly_rate: float
    budget: float | None
    status: ProjectStatus
    owner_id: uuid.UUID
    total_hours: float    # comes from Project.total_hours @property
    total_earned: float   # comes from Project.total_earned @property


class ProjectSummary(AppBaseSchema):
    """
    A lighter version for list endpoints — no need to send everything
    when showing a list of 20 projects. Less data = faster response.
    This is a common pattern called a DTO (Data Transfer Object).
    """
    id: uuid.UUID
    name: str
    client_name: str | None
    status: ProjectStatus
    total_hours: float
    total_earned: float


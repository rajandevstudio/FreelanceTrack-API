import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import AppBaseSchema, TimestampSchema


class TimeLogCreate(AppBaseSchema):
    """
    project_id is NOT here — it comes from the URL parameter.
    Example: POST /projects/{project_id}/logs
    The URL already tells us which project. No need to send it in the body too.
    Keeping the body clean reduces mistakes (wrong project_id in body vs URL).
    """
    hours: float = Field(gt=0, le=24)   # gt=0 → must be positive, le=24 → max 24h/day
    description: str | None = None
    work_date: date                      # just the date, not datetime


class TimeLogResponse(TimestampSchema):
    hours: float
    description: str | None
    work_date: date
    project_id: uuid.UUID


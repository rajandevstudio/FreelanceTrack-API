from app.schemas.base import AppBaseSchema
from app.schemas.project import ProjectSummary


class EarningsSummary(AppBaseSchema):
    """
    Aggregated stats across all projects for the logged-in user.
    This is computed in the service layer — not a direct DB model.
    That's why it inherits AppBaseSchema, not TimestampSchema
    (there's no single DB row behind this — it's calculated data).
    """
    total_projects: int
    active_projects: int
    completed_projects: int
    total_hours_logged: float
    total_earned: float
    projects: list[ProjectSummary]   # breakdown per project


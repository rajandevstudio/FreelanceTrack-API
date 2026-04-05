from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectSummary
from app.schemas.report import EarningsSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/earnings", response_model=EarningsSummary)
async def earnings_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EarningsSummary:
    """
    Aggregated earnings report for the logged-in user.
    Computes totals across all their projects.

    This is pure calculation in Python — no raw SQL aggregation.
    For larger datasets you'd push this into SQL (SUM, COUNT) for performance.
    For a freelancer with ~50 projects, Python-side is fine and simpler.
    """
    result = await db.execute(
        select(Project).where(
            Project.owner_id == current_user.id,
            Project.deleted == False,
        )
    )
    projects = result.scalars().all()

    # Build summaries and compute aggregates in Python
    project_summaries = [
        ProjectSummary(
            id=p.id,
            name=p.name,
            client_name=p.client_name,
            status=p.status,
            total_hours=p.total_hours,
            total_earned=p.total_earned,
        )
        for p in projects
    ]

    return EarningsSummary(
        total_projects=len(projects),
        active_projects=sum(1 for p in projects if p.status == ProjectStatus.ACTIVE),
        completed_projects=sum(1 for p in projects if p.status == ProjectStatus.COMPLETED),
        total_hours_logged=sum(p.total_hours for p in projects),
        total_earned=round(sum(p.total_earned for p in projects), 2),
        projects=project_summaries,
    )
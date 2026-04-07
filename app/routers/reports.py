from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectSummary
from app.schemas.report import EarningsSummary
from app.services.pdf_service import generate_invoice_pdf
from fastapi.responses import StreamingResponse
import io
import uuid
from fastapi import HTTPException, status



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


@router.get("/invoice/{project_id}")
async def download_invoice(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and download a PDF invoice for a specific project.

    Returns a StreamingResponse with the PDF bytes — no file is written
    to disk. The PDF is generated in memory and streamed directly to the
    client. Content-Disposition: attachment tells the browser to download
    it rather than try to render it inline.
    """
    # Fetch the project — must belong to current user
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
            Project.deleted == False,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    pdf_bytes = generate_invoice_pdf(
        project=project,
        owner_name=current_user.full_name,
    )

    invoice_number = f"INV-{str(project.id)[:8].upper()}"
    filename = f"{invoice_number}-{project.name.replace(' ', '-')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
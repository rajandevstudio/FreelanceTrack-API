import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.project import Project
from app.models.timelog import TimeLog
from app.models.user import User
from app.schemas.timelog import TimeLogCreate, TimeLogResponse

router = APIRouter(tags=["time logs"])

# -----------------------------------------------------------------------------
# NOTICE: no prefix here — because this router's URLs are nested under projects:
#   POST /projects/{project_id}/logs
#   GET  /projects/{project_id}/logs
#
# Nesting makes the relationship clear in the URL itself.
# A time log only makes sense in the context of a project.
# This is called a "nested resource" pattern — common in REST APIs.
# -----------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/logs",
    response_model=TimeLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_time(
    project_id: uuid.UUID,
    payload: TimeLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeLogResponse:
    """
    Log hours worked on a specific project.
    We verify the project belongs to current_user before allowing the log.
    You can't log time against someone else's project.
    """

    # First verify the project exists AND belongs to this user
    project = await _get_owned_project(db, project_id, current_user.id)

    time_log = TimeLog(
        **payload.model_dump(),
        project_id=project.id,
    )
    db.add(time_log)
    await db.flush()
    return time_log


@router.get(
    "/projects/{project_id}/logs",
    response_model=list[TimeLogResponse],
)
async def list_time_logs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimeLogResponse]:
    """
    List all time logs for a project.
    Ordered by work_date descending — most recent first.
    """
    # Verify ownership first
    await _get_owned_project(db, project_id, current_user.id)

    result = await db.execute(
        select(TimeLog)
        .where(
            TimeLog.project_id == project_id,
            TimeLog.deleted == False,
        )
        .order_by(TimeLog.work_date.desc())  # most recent first
    )
    return result.scalars().all()


@router.delete(
    "/projects/{project_id}/logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_time_log(
    project_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft delete a specific time log entry."""

    # Verify project ownership first
    await _get_owned_project(db, project_id, current_user.id)

    result = await db.execute(
        select(TimeLog).where(
            TimeLog.id == log_id,
            TimeLog.project_id == project_id,
            TimeLog.deleted == False,
        )
    )
    time_log = result.scalar_one_or_none()

    if not time_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time log not found",
        )

    time_log.deleted = True
    await db.flush()


async def _get_owned_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Project:
    """Verify a project exists and belongs to the user. Raises 404 otherwise."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
            Project.deleted == False,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project
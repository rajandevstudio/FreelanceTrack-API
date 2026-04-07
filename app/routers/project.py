import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.helpers.project_helpers import create_project_for_a_user, delete_project, get_project_by_id, get_projects
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectSummary, ProjectUpdate

# -----------------------------------------------------------------------------
# NOTICE THE DIFFERENCE FROM AUTH ROUTER
#
# Auth routes are public — anyone can hit /auth/register or /auth/login.
# Project routes are protected — every single one requires a valid JWT.
#
# We achieve this with ONE line per route:
#   current_user: User = Depends(get_current_user)
#
# FastAPI runs get_current_user before the route body.
# If the token is missing/invalid → 401, route never runs.
# If token is valid → current_user is the logged-in User object.
#
# This is much cleaner than Django where you'd use @login_required
# on every view or add middleware. Here the dependency IS the protection.
# -----------------------------------------------------------------------------

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=list[ProjectSummary], status_code=status.HTTP_200_OK)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectSummary]:
    """
    List all projects belonging to the logged-in user.
    Returns ProjectSummary (lighter) not ProjectResponse (full).
    For lists, send less data — faster response, less bandwidth.
    """
    return await get_projects(db, current_user)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Create a new project for the logged-in user.
    owner_id comes from the token — client never sends it.
    """
    return await create_project_for_a_user(db, payload, current_user)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,              # FastAPI parses and validates UUID from URL
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Get a single project by ID.
    We check owner_id == current_user.id — users can only see their own projects.
    This is called object-level authorization (vs route-level).
    """
    project = await _get_project_or_404(db, project_id, current_user.id)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Partially update a project. PATCH means only send what you want to change.
    If you only send {"status": "completed"}, only status updates.
    Other fields stay as they are.
    """
    project = await _get_project_or_404(db, project_id, current_user.id)

    # model_dump(exclude_unset=True) is key here —
    # it only returns fields the client actually sent, not fields that defaulted to None.
    # So {"status": "completed"} only gives {"status": "completed"}, not
    # {"status": "completed", "name": None, "description": None, ...}
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)  # update only the sent fields

    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_by_id(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Soft delete a project — sets deleted=True, doesn't remove from DB.
    204 No Content is the correct status for successful deletes — no body returned.
    """
    project = await _get_project_or_404(db, project_id, current_user.id)
    await delete_project(db, project)
    return None  # FastAPI ignores this and returns an empty response body


# -----------------------------------------------------------------------------
# PRIVATE HELPER — note the underscore prefix
#
# _get_project_or_404 is used by get, update, and delete — all three need
# to find a project AND verify ownership. Writing it once here means:
#   - No duplication
#   - If we change the logic (e.g. add team ownership later), one place to update
#
# The underscore prefix is a Python convention meaning "internal to this module".
# It's not enforced by Python but tells other developers: don't import this.
# -----------------------------------------------------------------------------

async def _get_project_or_404(
    db: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Project:
    """Fetch a project by ID and owner. Raises 404 if not found or not owned."""
    project = await get_project_by_id(db, project_id, owner_id)  # reuse the same query logic

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project
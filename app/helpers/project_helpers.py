import uuid
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectSummary

async def create_project_for_a_user(db: AsyncSession, payload, current_user: User) -> Project:
    """
    Create a new project for the logged-in user.
    owner_id comes from the token — client never sends it.
    """
    project = Project(
        **payload.model_dump(),          # unpack all validated fields from schema
        owner_id=current_user.id,        # set owner from token, not from request body
    )
    db.add(project)
    await db.flush()  # flush to get the ID assigned by the DB
    return project


async def get_projects(db: AsyncSession, current_user: User) -> list[ProjectSummary]:
    """
    List all projects belonging to the logged-in user.
    Returns ProjectSummary (lighter) not ProjectResponse (full).
    For lists, send less data — faster response, less bandwidth.
    """
    result = await db.execute(
        select(Project).where(
            Project.owner_id == current_user.id,
            Project.deleted == False,
        )
    )
    projects = result.scalars().all()
    return projects

async def get_project_by_id(db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project | None:
    """
    Fetch a project by ID. Returns None if not found, deleted, or doesn't belong to the user.
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
            Project.deleted == False,
        )
    )
    return result.scalar_one_or_none()  

async def delete_project(db: AsyncSession, project: Project) -> None:
    """
    Soft delete a project — sets deleted=True, doesn't remove from DB.
    """
    project.deleted = True
    await db.flush()
    return None

async def get_all_projects_for_user(db: AsyncSession, user_id) -> list[Project]:
    """
    Fetch all projects for a given user ID, including deleted ones.
    Used for admin views or analytics where we want the full picture.
    """
    result = await db.execute(
        select(Project).where(
            Project.owner_id == user_id,
        )
    )
    return result.scalars().all()
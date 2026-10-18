import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStats, ProjectUpdate
from app.schemas.review import ReviewResponse
from app.services import project_service, review_service

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(**data.model_dump(), user_id=current_user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await project_service.get_owned_project(db, project_id, current_user.id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.get_owned_project(db, project_id, current_user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.get_owned_project(db, project_id, current_user.id)
    await db.delete(project)
    await db.commit()


@router.get("/{project_id}/reviews", response_model=list[ReviewResponse])
async def list_project_reviews(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Історія рев'ю проєкту, нові першими."""
    await project_service.get_owned_project(db, project_id, current_user.id)
    return await review_service.list_project_reviews(db, project_id)


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Агрегати по проєкту: середня оцінка, розподіл за категоріями, динаміка оцінки."""
    await project_service.get_owned_project(db, project_id, current_user.id)
    return await project_service.compute_stats(db, project_id)

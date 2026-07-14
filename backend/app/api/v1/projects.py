from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.models.user import User
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectOut

router = APIRouter()

@router.get("/", response_model=List[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    List all projects scoped under the user's tenant organization.
    """
    stmt = select(Project).where(Project.org_id == current_user.org_id)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return projects

@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.RoleChecker(["Admin", "Manager"]))
):
    """
    Create a new project.
    Restricted to Admin and Manager roles.
    """
    db_project = Project(
        name=project_in.name,
        org_id=current_user.org_id
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

from fastapi import APIRouter, Depends
import databases
from app.database import get_db
from app.models import Project
from app.schemas import Project as ProjectSchema, ProjectCreate
from typing import Annotated

router = APIRouter()


@router.get("/projects", response_model=list[ProjectSchema])
async def get_projects(db: Annotated[databases.Database, Depends(get_db)]):
    """Get list of all projects"""
    rows = await db.fetch_all("SELECT id, name, color, extra_color FROM projects ORDER BY id")
    return [Project.from_row(row) for row in rows]


@router.post("/projects", response_model=ProjectSchema, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Annotated[databases.Database, Depends(get_db)]
):
    """Create a new project"""
    row = await db.fetch_one(
        "INSERT INTO projects (name, color, extra_color) VALUES (:name, :color, :extra_color) RETURNING id, name, color, extra_color",
        {"name": project.name, "color": project.color, "extra_color": project.extraColor}
    )
    return Project.from_row(row)

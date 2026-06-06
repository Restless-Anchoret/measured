from fastapi import APIRouter, Depends, Query
import databases
from app.database import get_db
from app.models import Project
from app.schemas import Project as ProjectSchema, ProjectCreate, ProjectSort
from typing import Annotated

router = APIRouter()


@router.get("/projects", response_model=list[ProjectSchema])
async def get_projects(
    db: Annotated[databases.Database, Depends(get_db)],
    sort: ProjectSort = Query(default=ProjectSort.DEFAULT),
):
    """Get list of all projects"""
    project_rows = await db.fetch_all("SELECT id, name, color, extra_color FROM projects ORDER BY id")
    projects = [Project.from_row(row) for row in project_rows]

    if sort == ProjectSort.MOST_RECENTLY_USED:
        count_rows = await db.fetch_all(
            "SELECT project_id, COUNT(*) as session_count"
            " FROM (SELECT project_id FROM sessions ORDER BY id DESC LIMIT 100)"
            " GROUP BY project_id"
        )
        session_counts = {row["project_id"]: row["session_count"] for row in count_rows}
        projects.sort(key=lambda p: (-session_counts.get(p.id, 0), p.id))

    return projects


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

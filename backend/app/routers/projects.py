from fastapi import APIRouter, Depends
import databases
from app.database import get_db
from app.models import Project
from app.schemas import Project as ProjectSchema
from typing import Annotated

router = APIRouter()


@router.get("/projects", response_model=list[ProjectSchema])
async def get_projects(db: Annotated[databases.Database, Depends(get_db)]):
    """Get list of all projects"""
    rows = await db.fetch_all("SELECT id, name FROM projects ORDER BY id")
    return [Project.from_row(row) for row in rows]

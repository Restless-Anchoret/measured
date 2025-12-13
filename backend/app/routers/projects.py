from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import Project

router = APIRouter()


@router.get("/projects", response_model=list[Project])
async def get_projects(db: Session = Depends(get_db)):
    """Get list of all projects"""
    projects = db.query(models.Project).all()
    return projects


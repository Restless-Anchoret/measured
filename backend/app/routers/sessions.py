from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from app.schemas import Session as SessionSchema, SessionCreate, SessionUpdate, PaginatedSessions

router = APIRouter()


@router.post("/sessions", response_model=SessionSchema, status_code=201)
async def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new session"""
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == session.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create session
    db_session = models.Session(
        project_id=session.project_id,
        start_time=session.start_time,
        end_time=session.end_time
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.get("/sessions", response_model=PaginatedSessions)
async def get_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get paginated list of sessions"""
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get total count
    total = db.query(func.count(models.Session.id)).scalar()
    
    # Get sessions with pagination
    sessions = db.query(models.Session).order_by(models.Session.created_at.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedSessions(
        items=sessions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/sessions/{session_id}", response_model=SessionSchema)
async def update_session(
    session_id: int,
    session_update: SessionUpdate,
    db: Session = Depends(get_db)
):
    """Update a session's start_time and end_time"""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db_session.start_time = session_update.start_time
    db_session.end_time = session_update.end_time
    db.commit()
    db.refresh(db_session)
    return db_session


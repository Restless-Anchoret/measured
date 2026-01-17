from fastapi import APIRouter, Depends, HTTPException, Query
import databases
from app.database import get_db
from app.models import Session
from app.schemas import Session as SessionSchema, SessionCreate, SessionUpdate, PaginatedSessions
from typing import Annotated

router = APIRouter()


@router.post("/sessions", response_model=SessionSchema, status_code=201)
async def create_session(
    session: SessionCreate,
    db: Annotated[databases.Database, Depends(get_db)]
):
    """Create a new session"""
    # Verify project exists
    project_row = await db.fetch_one(
        "SELECT id FROM projects WHERE id = :project_id",
        {"project_id": session.project_id}
    )
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create session
    await db.execute(
        """
        INSERT INTO sessions (project_id, start_time, end_time)
        VALUES (:project_id, :start_time, :end_time)
        """,
        {
            "project_id": session.project_id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None
        }
    )
    
    # Get the created session
    row = await db.fetch_one(
        "SELECT * FROM sessions WHERE id = last_insert_rowid()"
    )
    return Session.from_row(row)


@router.get("/sessions", response_model=PaginatedSessions)
async def get_sessions(
    db: Annotated[databases.Database, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get paginated list of sessions"""
    offset = (page - 1) * page_size
    
    # Get total count
    total_row = await db.fetch_one("SELECT COUNT(*) as total FROM sessions")
    total = total_row["total"]
    
    # Get sessions with pagination
    rows = await db.fetch_all(
        """
        SELECT * FROM sessions
        ORDER BY created_at DESC
        LIMIT :page_size OFFSET :offset
        """,
        {"page_size": page_size, "offset": offset}
    )
    sessions = [Session.from_row(row) for row in rows]
    
    return PaginatedSessions(
        items=sessions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/sessions/{session_id}", response_model=SessionSchema)
async def get_session(
    session_id: int,
    db: Annotated[databases.Database, Depends(get_db)]
):
    """Get a single session by ID"""
    row = await db.fetch_one(
        "SELECT * FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return Session.from_row(row)


@router.put("/sessions/{session_id}", response_model=SessionSchema)
async def update_session(
    session_id: int,
    session_update: SessionUpdate,
    db: Annotated[databases.Database, Depends(get_db)]
):
    """Update a session's start_time and end_time"""
    # Check if session exists
    row = await db.fetch_one(
        "SELECT id FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session
    await db.execute(
        """
        UPDATE sessions
        SET start_time = :start_time, end_time = :end_time
        WHERE id = :session_id
        """,
        {
            "start_time": session_update.start_time.isoformat(),
            "end_time": session_update.end_time.isoformat(),
            "session_id": session_id
        }
    )
    
    # Get the updated session
    row = await db.fetch_one(
        "SELECT * FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    return Session.from_row(row)

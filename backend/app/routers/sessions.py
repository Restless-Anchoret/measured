from fastapi import APIRouter, Depends, HTTPException, Query
import databases
from app.database import get_db
from app.models import Session
from app.schemas import Session as SessionSchema, SessionCreate, SessionUpdate, PaginatedSessions
from typing import Annotated, Optional
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

router = APIRouter()

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


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

    if session.date is not None and session.duration_minutes is not None:
        date = session.date.isoformat()
        duration_minutes = session.duration_minutes
        start_time_value = None
        end_time_value = None
    else:
        date = session.start_time.astimezone(AMSTERDAM_TZ).date().isoformat()
        duration_minutes = (
            int((session.end_time - session.start_time).total_seconds() / 60)
            if session.end_time else None
        )
        start_time_value = session.start_time.isoformat()
        end_time_value = session.end_time.isoformat()

    now = datetime.now(timezone.utc)
    create_time = (now - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(milliseconds=1)

    # Create session using RETURNING clause (SQLite 3.35+)
    row = await db.fetch_one(
        """
        INSERT INTO sessions (project_id, start_time, end_time, created_at, date, duration_minutes, create_time)
        VALUES (:project_id, :start_time, :end_time, :created_at, :date, :duration_minutes, :create_time)
        RETURNING *
        """,
        {
            "project_id": session.project_id,
            "start_time": start_time_value,
            "end_time": end_time_value,
            "created_at": now.isoformat(),
            "date": date,
            "duration_minutes": duration_minutes,
            "create_time": create_time,
        }
    )
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return Session.from_row(row)


@router.get("/sessions", response_model=PaginatedSessions)
async def get_sessions(
    db: Annotated[databases.Database, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=5000),
    min_start_time: Optional[datetime] = Query(None, description="Minimum start time (inclusive) as UTC timestamp"),
    max_start_time: Optional[datetime] = Query(None, description="Maximum start time (exclusive) as UTC timestamp"),
    min_date: Optional[date] = Query(None, description="Minimum date (inclusive)"),
    max_date: Optional[date] = Query(None, description="Maximum date (exclusive)"),
    project_id: Optional[list[int]] = Query(None, description="Filter by one or more project IDs")
):
    """Get paginated list of sessions"""
    offset = (page - 1) * page_size

    # Build WHERE clause and params
    where_clauses = []
    filter_params = {}

    if min_start_time:
        where_clauses.append("start_time >= :min_start_time")
        filter_params["min_start_time"] = min_start_time.isoformat()

    if max_start_time:
        where_clauses.append("start_time < :max_start_time")
        filter_params["max_start_time"] = max_start_time.isoformat()

    if min_date:
        where_clauses.append("date >= :min_date")
        filter_params["min_date"] = min_date.isoformat()

    if max_date:
        where_clauses.append("date < :max_date")
        filter_params["max_date"] = max_date.isoformat()

    if project_id:
        # Build IN clause for multiple project IDs
        placeholders = ",".join([f":project_id_{i}" for i in range(len(project_id))])
        where_clauses.append(f"project_id IN ({placeholders})")
        for i, pid in enumerate(project_id):
            filter_params[f"project_id_{i}"] = pid
    
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Get total count
    count_query = f"SELECT COUNT(*) as total FROM sessions{where_sql}"
    total_row = await db.fetch_one(count_query, filter_params)
    total = total_row["total"]
    
    # Get sessions with pagination
    data_query = f"""
        SELECT * FROM sessions
        {where_sql}
        ORDER BY date DESC, id DESC
        LIMIT :page_size OFFSET :offset
    """
    data_params = {**filter_params, "page_size": page_size, "offset": offset}
    rows = await db.fetch_all(data_query, data_params)
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

    if session_update.date is not None and session_update.duration_minutes is not None:
        date = session_update.date.isoformat()
        duration_minutes = session_update.duration_minutes
        start_time_value = None
        end_time_value = None
    else:
        date = session_update.start_time.astimezone(AMSTERDAM_TZ).date().isoformat()
        duration_minutes = int((session_update.end_time - session_update.start_time).total_seconds() / 60)
        start_time_value = session_update.start_time.isoformat()
        end_time_value = session_update.end_time.isoformat()

    # Update session
    await db.execute(
        """
        UPDATE sessions
        SET start_time = :start_time, end_time = :end_time, date = :date, duration_minutes = :duration_minutes
        WHERE id = :session_id
        """,
        {
            "start_time": start_time_value,
            "end_time": end_time_value,
            "date": date,
            "duration_minutes": duration_minutes,
            "session_id": session_id
        }
    )
    
    # Get the updated session
    row = await db.fetch_one(
        "SELECT * FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    return Session.from_row(row)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    db: Annotated[databases.Database, Depends(get_db)]
):
    """Delete a session by ID"""
    # Check if session exists
    row = await db.fetch_one(
        "SELECT id FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete the session
    await db.execute(
        "DELETE FROM sessions WHERE id = :session_id",
        {"session_id": session_id}
    )

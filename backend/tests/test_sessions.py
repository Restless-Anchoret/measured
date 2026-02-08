"""
Integration tests for the sessions endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from typing import Optional


# Helper functions
async def get_first_project_id(client: AsyncClient) -> int:
    """Get the first project ID from the projects endpoint."""
    projects_response = await client.get("/api/projects")
    return projects_response.json()[0]["id"]


async def create_session(
    client: AsyncClient,
    project_id: int,
    start_time: datetime,
    end_time: Optional[datetime] = None
) -> dict:
    """Create a session and return the response JSON."""
    session_data = {
        "project_id": project_id,
        "start_time": start_time.isoformat(),
    }
    if end_time is not None:
        session_data["end_time"] = end_time.isoformat()
    
    response = await client.post("/api/sessions", json=session_data)
    return response.json()


async def create_multiple_sessions(
    client: AsyncClient,
    project_id: int,
    start_times: list[datetime],
    duration: timedelta = timedelta(hours=1)
) -> list[dict]:
    """Create multiple sessions with given start times and a fixed duration."""
    sessions = []
    for start_time in start_times:
        session = await create_session(
            client,
            project_id,
            start_time,
            start_time + duration
        )
        sessions.append(session)
    return sessions


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Test creating a new session."""
    project_id = await get_first_project_id(client)
    
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now()
    
    session_data = {
        "project_id": project_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    response = await client.post("/api/sessions", json=session_data)
    
    assert response.status_code == 201
    session = response.json()
    
    assert "id" in session
    assert session["project_id"] == project_id
    assert session["start_time"] is not None
    assert session["end_time"] is not None
    assert "created_at" in session


@pytest.mark.asyncio
async def test_create_session_without_end_time(client: AsyncClient):
    """Test creating a session without end_time."""
    project_id = await get_first_project_id(client)
    
    start_time = datetime.now()
    session_data = {
        "project_id": project_id,
        "start_time": start_time.isoformat()
    }
    
    response = await client.post("/api/sessions", json=session_data)
    
    assert response.status_code == 201
    session = response.json()
    
    assert session["project_id"] == project_id
    assert session["start_time"] is not None
    assert session["end_time"] is None


@pytest.mark.asyncio
async def test_create_session_invalid_project(client: AsyncClient):
    """Test creating a session with non-existent project ID."""
    start_time = datetime.now()
    session_data = {
        "project_id": 99999,  # Non-existent project
        "start_time": start_time.isoformat()
    }
    
    response = await client.post("/api/sessions", json=session_data)
    
    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_sessions_empty(client: AsyncClient):
    """Test getting sessions when there are none."""
    response = await client.get("/api/sessions")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_get_sessions_paginated(client: AsyncClient):
    """Test getting paginated sessions."""
    project_id = await get_first_project_id(client)
    
    # Create 5 sessions
    start_times = [datetime.now() - timedelta(hours=i+1) for i in range(5)]
    await create_multiple_sessions(client, project_id, start_times, duration=timedelta(hours=1))
    
    # Get first page
    response = await client.get("/api/sessions?page=1&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    
    # Get second page
    response = await client.get("/api/sessions?page=2&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["items"]) == 2
    assert data["page"] == 2
    
    # Get third page
    response = await client.get("/api/sessions?page=3&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["items"]) == 1
    assert data["page"] == 3
    
    # Verify sessions are ordered by start_time DESC (most recent first)
    all_sessions_response = await client.get("/api/sessions?page=1&page_size=100")
    all_sessions = all_sessions_response.json()["items"]
    start_times = [s["start_time"] for s in all_sessions]
    # Should be in descending order
    assert start_times == sorted(start_times, reverse=True)


@pytest.mark.asyncio
async def test_get_sessions_pagination_validation(client: AsyncClient):
    """Test pagination query parameter validation."""
    # Test invalid page (less than 1)
    response = await client.get("/api/sessions?page=0")
    assert response.status_code == 400
    
    # Test invalid page_size (less than 1)
    response = await client.get("/api/sessions?page_size=0")
    assert response.status_code == 400
    
    # Test page_size too large (greater than 100)
    response = await client.get("/api/sessions?page_size=101")
    assert response.status_code == 400
    
    # Test valid parameters
    response = await client.get("/api/sessions?page=1&page_size=50")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_session_by_id(client: AsyncClient):
    """Test getting a single session by ID."""
    project_id = await get_first_project_id(client)
    
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now()
    
    created_session = await create_session(client, project_id, start_time, end_time)
    session_id = created_session["id"]
    
    # Get the session by ID
    response = await client.get(f"/api/sessions/{session_id}")
    
    assert response.status_code == 200
    session = response.json()
    
    assert session["id"] == session_id
    assert session["project_id"] == project_id
    assert session["start_time"] == created_session["start_time"]
    assert session["end_time"] == created_session["end_time"]


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    """Test getting a non-existent session."""
    response = await client.get("/api/sessions/99999")
    
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_session(client: AsyncClient):
    """Test updating a session."""
    project_id = await get_first_project_id(client)
    
    start_time = datetime.now() - timedelta(hours=3)
    end_time = datetime.now() - timedelta(hours=2)
    
    created_session = await create_session(client, project_id, start_time, end_time)
    session_id = created_session["id"]
    
    # Update the session
    new_start_time = datetime.now() - timedelta(hours=4)
    new_end_time = datetime.now() - timedelta(hours=1)
    update_data = {
        "start_time": new_start_time.isoformat(),
        "end_time": new_end_time.isoformat()
    }
    
    response = await client.put(f"/api/sessions/{session_id}", json=update_data)
    
    assert response.status_code == 200
    updated_session = response.json()
    
    assert updated_session["id"] == session_id
    assert updated_session["project_id"] == project_id
    assert updated_session["start_time"] == new_start_time.isoformat()
    assert updated_session["end_time"] == new_end_time.isoformat()
    # created_at should not change
    assert updated_session["created_at"] == created_session["created_at"]


@pytest.mark.asyncio
async def test_update_session_not_found(client: AsyncClient):
    """Test updating a non-existent session."""
    new_start_time = datetime.now() - timedelta(hours=4)
    new_end_time = datetime.now() - timedelta(hours=1)
    update_data = {
        "start_time": new_start_time.isoformat(),
        "end_time": new_end_time.isoformat()
    }
    
    response = await client.put("/api/sessions/99999", json=update_data)
    
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_sessions_with_min_start_time_filter(client: AsyncClient):
    """Test filtering sessions with min_start_time (inclusive)."""
    project_id = await get_first_project_id(client)
    
    base_time = datetime(2024, 1, 15, 12, 0, 0)
    session_times = [
        base_time - timedelta(hours=6),  # 06:00
        base_time - timedelta(hours=3),  # 09:00
        base_time,                        # 12:00
        base_time + timedelta(hours=3),  # 15:00
        base_time + timedelta(hours=6),  # 18:00
    ]
    
    await create_multiple_sessions(client, project_id, session_times)
    
    # Filter with min_start_time at 12:00 (should get 12:00, 15:00, 18:00 - inclusive)
    min_time = base_time.isoformat()
    response = await client.get(f"/api/sessions?min_start_time={min_time}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should get 3 sessions (12:00, 15:00, 18:00)
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Verify all returned sessions have start_time >= min_time
    for session in data["items"]:
        assert session["start_time"] >= min_time


@pytest.mark.asyncio
async def test_get_sessions_with_max_start_time_filter(client: AsyncClient):
    """Test filtering sessions with max_start_time (exclusive)."""
    project_id = await get_first_project_id(client)
    
    base_time = datetime(2024, 2, 20, 12, 0, 0)
    session_times = [
        base_time - timedelta(hours=6),  # 06:00
        base_time - timedelta(hours=3),  # 09:00
        base_time,                        # 12:00
        base_time + timedelta(hours=3),  # 15:00
        base_time + timedelta(hours=6),  # 18:00
    ]
    
    await create_multiple_sessions(client, project_id, session_times)
    
    # Filter with max_start_time at 12:00 (should get 06:00, 09:00 - exclusive)
    max_time = base_time.isoformat()
    response = await client.get(f"/api/sessions?max_start_time={max_time}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should get 2 sessions (06:00, 09:00) - 12:00 is excluded
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # Verify all returned sessions have start_time < max_time
    for session in data["items"]:
        assert session["start_time"] < max_time


@pytest.mark.asyncio
async def test_get_sessions_with_both_time_filters(client: AsyncClient):
    """Test filtering sessions with both min_start_time and max_start_time."""
    project_id = await get_first_project_id(client)
    
    base_time = datetime(2024, 3, 10, 12, 0, 0)
    session_times = [
        base_time - timedelta(hours=9),  # 03:00
        base_time - timedelta(hours=6),  # 06:00
        base_time - timedelta(hours=3),  # 09:00
        base_time,                        # 12:00
        base_time + timedelta(hours=3),  # 15:00
        base_time + timedelta(hours=6),  # 18:00
        base_time + timedelta(hours=9),  # 21:00
    ]
    
    await create_multiple_sessions(client, project_id, session_times)
    
    # Filter with min_start_time at 06:00 and max_start_time at 18:00
    # Should get: 06:00, 09:00, 12:00, 15:00 (18:00 is excluded)
    min_time = (base_time - timedelta(hours=6)).isoformat()
    max_time = (base_time + timedelta(hours=6)).isoformat()
    response = await client.get(f"/api/sessions?min_start_time={min_time}&max_start_time={max_time}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should get 4 sessions
    assert data["total"] == 4
    assert len(data["items"]) == 4
    
    # Verify all returned sessions are within the range
    for session in data["items"]:
        assert session["start_time"] >= min_time
        assert session["start_time"] < max_time


@pytest.mark.asyncio
async def test_get_sessions_time_filter_no_results(client: AsyncClient):
    """Test time filters that return no results."""
    project_id = await get_first_project_id(client)
    
    session_time = datetime(2024, 4, 1, 12, 0, 0)
    await create_session(client, project_id, session_time, session_time + timedelta(hours=1))
    
    # Filter with a time range that doesn't include the session
    min_time = (session_time + timedelta(days=1)).isoformat()
    max_time = (session_time + timedelta(days=2)).isoformat()
    response = await client.get(f"/api/sessions?min_start_time={min_time}&max_start_time={max_time}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_get_sessions_time_filter_with_pagination(client: AsyncClient):
    """Test time filters combined with pagination."""
    project_id = await get_first_project_id(client)
    
    base_time = datetime(2024, 5, 1, 12, 0, 0)
    
    # Create 5 sessions within a specific time range
    start_times = [base_time + timedelta(hours=i) for i in range(5)]
    await create_multiple_sessions(client, project_id, start_times, duration=timedelta(minutes=30))
    
    # Filter to get all 5 sessions, but paginate with page_size=2
    min_time = base_time.isoformat()
    max_time = (base_time + timedelta(hours=5)).isoformat()
    
    # First page
    response = await client.get(
        f"/api/sessions?min_start_time={min_time}&max_start_time={max_time}&page=1&page_size=2"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    
    # Second page
    response = await client.get(
        f"/api/sessions?min_start_time={min_time}&max_start_time={max_time}&page=2&page_size=2"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_get_sessions_invalid_min_start_time(client: AsyncClient):
    """Test invalid min_start_time format returns 400."""
    response = await client.get("/api/sessions?min_start_time=invalid-datetime")
    
    # Should return 400 (not 422) due to our custom exception handler
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_sessions_invalid_max_start_time(client: AsyncClient):
    """Test invalid max_start_time format returns 400."""
    response = await client.get("/api/sessions?max_start_time=not-a-date")
    
    # Should return 400 (not 422) due to our custom exception handler
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_sessions_time_filter_boundary(client: AsyncClient):
    """Test boundary conditions for time filters (inclusive min, exclusive max)."""
    project_id = await get_first_project_id(client)
    
    boundary_time = datetime(2024, 6, 15, 10, 30, 0)
    await create_session(client, project_id, boundary_time, boundary_time + timedelta(hours=1))
    
    # Test min_start_time with exact boundary (should be included - inclusive)
    response = await client.get(f"/api/sessions?min_start_time={boundary_time.isoformat()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    
    # Test max_start_time with exact boundary (should be excluded - exclusive)
    response = await client.get(f"/api/sessions?max_start_time={boundary_time.isoformat()}")
    assert response.status_code == 200
    data = response.json()
    # The session at boundary_time should not be included
    for session in data["items"]:
        assert session["start_time"] != boundary_time.isoformat()


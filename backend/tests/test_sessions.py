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
    all_sessions_response = await client.get("/api/sessions?page=1&page_size=1000")
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
    
    # Test page_size too large (greater than 1000)
    response = await client.get("/api/sessions?page_size=1001")
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


@pytest.mark.asyncio
async def test_get_sessions_filter_by_single_project(client: AsyncClient):
    """Test filtering sessions by a single project ID."""
    # Get first two projects
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 2, "Need at least 2 projects for this test"
    
    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]
    
    base_time = datetime(2024, 7, 1, 12, 0, 0)
    
    # Create 3 sessions for project 1
    for i in range(3):
        await create_session(
            client,
            project1_id,
            base_time + timedelta(hours=i),
            base_time + timedelta(hours=i, minutes=30)
        )
    
    # Create 2 sessions for project 2
    for i in range(2):
        await create_session(
            client,
            project2_id,
            base_time + timedelta(hours=i+3),
            base_time + timedelta(hours=i+3, minutes=30)
        )
    
    # Filter by project 1 only
    response = await client.get(f"/api/sessions?project_id={project1_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Verify all returned sessions belong to project 1
    for session in data["items"]:
        assert session["project_id"] == project1_id


@pytest.mark.asyncio
async def test_get_sessions_filter_by_multiple_projects(client: AsyncClient):
    """Test filtering sessions by multiple project IDs."""
    # Get first three projects
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 3, "Need at least 3 projects for this test"
    
    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]
    project3_id = projects[2]["id"]
    
    base_time = datetime(2024, 8, 1, 12, 0, 0)
    
    # Create sessions for each project
    await create_session(client, project1_id, base_time, base_time + timedelta(hours=1))
    await create_session(client, project1_id, base_time + timedelta(hours=1), base_time + timedelta(hours=2))
    await create_session(client, project2_id, base_time + timedelta(hours=2), base_time + timedelta(hours=3))
    await create_session(client, project3_id, base_time + timedelta(hours=3), base_time + timedelta(hours=4))
    
    # Filter by projects 1 and 2 (should get 3 sessions total)
    response = await client.get(f"/api/sessions?project_id={project1_id}&project_id={project2_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Verify all returned sessions belong to project 1 or project 2
    for session in data["items"]:
        assert session["project_id"] in [project1_id, project2_id]
    
    # Verify project 3 session is not included
    project_ids_in_results = [s["project_id"] for s in data["items"]]
    assert project3_id not in project_ids_in_results


@pytest.mark.asyncio
async def test_get_sessions_filter_by_project_no_results(client: AsyncClient):
    """Test filtering by a project that has no sessions."""
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 2, "Need at least 2 projects for this test"
    
    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]
    
    # Create sessions only for project 1
    base_time = datetime(2024, 9, 1, 12, 0, 0)
    await create_session(client, project1_id, base_time, base_time + timedelta(hours=1))
    
    # Filter by project 2 (should return no results)
    response = await client.get(f"/api/sessions?project_id={project2_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_get_sessions_filter_by_project_with_time_filters(client: AsyncClient):
    """Test combining project_id filter with time filters."""
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 2, "Need at least 2 projects for this test"
    
    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]
    
    base_time = datetime(2024, 10, 1, 12, 0, 0)
    
    # Create sessions for project 1 at different times
    await create_session(client, project1_id, base_time, base_time + timedelta(hours=1))
    await create_session(client, project1_id, base_time + timedelta(hours=5), base_time + timedelta(hours=6))
    
    # Create sessions for project 2 at different times
    await create_session(client, project2_id, base_time + timedelta(hours=2), base_time + timedelta(hours=3))
    await create_session(client, project2_id, base_time + timedelta(hours=7), base_time + timedelta(hours=8))
    
    # Filter by project 1 with time range that only includes the second session
    min_time = (base_time + timedelta(hours=4)).isoformat()
    max_time = (base_time + timedelta(hours=7)).isoformat()
    response = await client.get(f"/api/sessions?project_id={project1_id}&min_start_time={min_time}&max_start_time={max_time}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only get 1 session (project 1, starting at 17:00)
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["project_id"] == project1_id
    assert data["items"][0]["start_time"] >= min_time
    assert data["items"][0]["start_time"] < max_time


@pytest.mark.asyncio
async def test_get_sessions_filter_by_project_with_pagination(client: AsyncClient):
    """Test filtering by project ID with pagination."""
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    project_id = projects[0]["id"]
    
    base_time = datetime(2024, 11, 1, 12, 0, 0)
    
    # Create 5 sessions for the project
    start_times = [base_time + timedelta(hours=i) for i in range(5)]
    await create_multiple_sessions(client, project_id, start_times, duration=timedelta(hours=1))
    
    # Filter by project with pagination (page_size=2)
    response = await client.get(f"/api/sessions?project_id={project_id}&page=1&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    
    # All items should belong to the filtered project
    for session in data["items"]:
        assert session["project_id"] == project_id


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient):
    """Test deleting an existing session."""
    project_id = await get_first_project_id(client)
    
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now()
    
    # Create a session
    created_session = await create_session(client, project_id, start_time, end_time)
    session_id = created_session["id"]
    
    # Verify session exists
    get_response = await client.get(f"/api/sessions/{session_id}")
    assert get_response.status_code == 200
    
    # Delete the session
    delete_response = await client.delete(f"/api/sessions/{session_id}")
    
    assert delete_response.status_code == 204
    assert delete_response.content == b''  # No content for 204 response
    
    # Verify session is deleted (should return 404)
    get_after_delete = await client.get(f"/api/sessions/{session_id}")
    assert get_after_delete.status_code == 404
    assert "Session not found" in get_after_delete.json()["detail"]


@pytest.mark.asyncio
async def test_delete_session_not_found(client: AsyncClient):
    """Test deleting a non-existent session."""
    response = await client.delete("/api/sessions/99999")
    
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_session_does_not_affect_others(client: AsyncClient):
    """Test that deleting a session doesn't affect other sessions."""
    project_id = await get_first_project_id(client)
    
    base_time = datetime(2024, 12, 1, 12, 0, 0)
    
    # Create 3 sessions
    session1 = await create_session(client, project_id, base_time, base_time + timedelta(hours=1))
    session2 = await create_session(client, project_id, base_time + timedelta(hours=2), base_time + timedelta(hours=3))
    session3 = await create_session(client, project_id, base_time + timedelta(hours=4), base_time + timedelta(hours=5))
    
    # Delete the middle session
    delete_response = await client.delete(f"/api/sessions/{session2['id']}")
    assert delete_response.status_code == 204
    
    # Verify session2 is deleted
    get_session2 = await client.get(f"/api/sessions/{session2['id']}")
    assert get_session2.status_code == 404
    
    # Verify session1 and session3 still exist
    get_session1 = await client.get(f"/api/sessions/{session1['id']}")
    assert get_session1.status_code == 200
    assert get_session1.json()["id"] == session1["id"]
    
    get_session3 = await client.get(f"/api/sessions/{session3['id']}")
    assert get_session3.status_code == 200
    assert get_session3.json()["id"] == session3["id"]
    
    # Verify total count is 2
    sessions_response = await client.get("/api/sessions")
    data = sessions_response.json()
    assert data["total"] == 2


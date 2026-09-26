"""
Integration tests for the sessions endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import date


# Helper functions
async def get_first_project_id(client: AsyncClient) -> int:
    """Get the first project ID from the projects endpoint."""
    projects_response = await client.get("/api/projects")
    return projects_response.json()[0]["id"]


async def create_session(
    client: AsyncClient,
    project_id: int,
    session_date: date,
    duration_minutes: int = 60
) -> dict:
    """Create a session and return the response JSON."""
    session_data = {
        "project_id": project_id,
        "date": session_date.isoformat(),
        "duration_minutes": duration_minutes,
    }
    response = await client.post("/api/sessions", json=session_data)
    return response.json()


async def create_multiple_sessions(
    client: AsyncClient,
    project_id: int,
    dates: list[date],
    duration_minutes: int = 60
) -> list[dict]:
    """Create multiple sessions with given dates and a fixed duration."""
    sessions = []
    for session_date in dates:
        session = await create_session(client, project_id, session_date, duration_minutes)
        sessions.append(session)
    return sessions


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Test creating a new session."""
    project_id = await get_first_project_id(client)

    session_data = {
        "project_id": project_id,
        "date": "2026-06-15",
        "duration_minutes": 45,
    }

    response = await client.post("/api/sessions", json=session_data)

    assert response.status_code == 201
    session = response.json()

    assert "id" in session
    assert session["project_id"] == project_id
    assert session["date"] == "2026-06-15"
    assert session["duration_minutes"] == 45


@pytest.mark.asyncio
async def test_create_session_missing_fields(client: AsyncClient):
    """Test creating a session without date/duration_minutes returns 400."""
    project_id = await get_first_project_id(client)

    response = await client.post("/api/sessions", json={"project_id": project_id})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_session_invalid_project(client: AsyncClient):
    """Test creating a session with non-existent project ID."""
    session_data = {
        "project_id": 99999,  # Non-existent project
        "date": "2026-06-15",
        "duration_minutes": 45,
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

    # Create 5 sessions on different dates
    dates = [date(2026, 6, 10 + i) for i in range(5)]
    await create_multiple_sessions(client, project_id, dates)

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

    # Verify sessions are ordered by date DESC, id DESC (most recent first)
    all_sessions_response = await client.get("/api/sessions?page=1&page_size=1000")
    all_sessions = all_sessions_response.json()["items"]
    sort_keys = [(s["date"], s["id"]) for s in all_sessions]
    # Should be in descending order
    assert sort_keys == sorted(sort_keys, reverse=True)


@pytest.mark.asyncio
async def test_get_sessions_pagination_validation(client: AsyncClient):
    """Test pagination query parameter validation."""
    # Test invalid page (less than 1)
    response = await client.get("/api/sessions?page=0")
    assert response.status_code == 400

    # Test invalid page_size (less than 1)
    response = await client.get("/api/sessions?page_size=0")
    assert response.status_code == 400

    # Test page_size too large (greater than 5000)
    response = await client.get("/api/sessions?page_size=5001")
    assert response.status_code == 400

    # Test valid parameters
    response = await client.get("/api/sessions?page=1&page_size=50")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_session_by_id(client: AsyncClient):
    """Test getting a single session by ID."""
    project_id = await get_first_project_id(client)

    created_session = await create_session(client, project_id, date(2026, 6, 15), 90)
    session_id = created_session["id"]

    # Get the session by ID
    response = await client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 200
    session = response.json()

    assert session["id"] == session_id
    assert session["project_id"] == project_id
    assert session["date"] == created_session["date"]
    assert session["duration_minutes"] == created_session["duration_minutes"]


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

    created_session = await create_session(client, project_id, date(2026, 6, 10), 60)
    session_id = created_session["id"]

    update_data = {"date": "2026-06-15", "duration_minutes": 45}
    response = await client.put(f"/api/sessions/{session_id}", json=update_data)

    assert response.status_code == 200
    updated_session = response.json()

    assert updated_session["id"] == session_id
    assert updated_session["project_id"] == project_id
    assert updated_session["date"] == "2026-06-15"
    assert updated_session["duration_minutes"] == 45


@pytest.mark.asyncio
async def test_update_session_missing_fields(client: AsyncClient):
    """Test updating a session without date/duration_minutes returns 400."""
    project_id = await get_first_project_id(client)

    created_session = await create_session(client, project_id, date(2026, 6, 10), 60)
    session_id = created_session["id"]

    response = await client.put(f"/api/sessions/{session_id}", json={})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_session_not_found(client: AsyncClient):
    """Test updating a non-existent session."""
    update_data = {"date": "2026-06-15", "duration_minutes": 45}

    response = await client.put("/api/sessions/99999", json=update_data)

    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_sessions_with_min_date_filter(client: AsyncClient):
    """Test filtering sessions with min_date (inclusive)."""
    project_id = await get_first_project_id(client)

    dates = [date(2024, 1, d) for d in [9, 12, 15, 18, 21]]
    await create_multiple_sessions(client, project_id, dates)

    # Filter with min_date at 2024-01-15 (should get 15, 18, 21 - inclusive)
    response = await client.get("/api/sessions?min_date=2024-01-15")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    for session in data["items"]:
        assert session["date"] >= "2024-01-15"


@pytest.mark.asyncio
async def test_get_sessions_with_max_date_filter(client: AsyncClient):
    """Test filtering sessions with max_date (exclusive)."""
    project_id = await get_first_project_id(client)

    dates = [date(2024, 2, d) for d in [17, 19, 20, 21, 23]]
    await create_multiple_sessions(client, project_id, dates)

    # Filter with max_date at 2024-02-20 (should get 17, 19 - exclusive)
    response = await client.get("/api/sessions?max_date=2024-02-20")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    for session in data["items"]:
        assert session["date"] < "2024-02-20"


@pytest.mark.asyncio
async def test_get_sessions_with_both_date_filters(client: AsyncClient):
    """Test filtering sessions with both min_date and max_date."""
    project_id = await get_first_project_id(client)

    dates = [date(2024, 3, d) for d in [1, 4, 7, 10, 13, 16, 19]]
    await create_multiple_sessions(client, project_id, dates)

    # Filter with min_date at 03-04 and max_date at 03-16
    # Should get: 04, 07, 10, 13 (16 is excluded)
    response = await client.get("/api/sessions?min_date=2024-03-04&max_date=2024-03-16")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 4
    for session in data["items"]:
        assert session["date"] >= "2024-03-04"
        assert session["date"] < "2024-03-16"


@pytest.mark.asyncio
async def test_get_sessions_date_filter_no_results(client: AsyncClient):
    """Test date filters that return no results."""
    project_id = await get_first_project_id(client)

    await create_session(client, project_id, date(2024, 4, 1))

    # Filter with a date range that doesn't include the session
    response = await client.get("/api/sessions?min_date=2024-05-01&max_date=2024-06-01")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_get_sessions_date_filter_with_pagination(client: AsyncClient):
    """Test date filters combined with pagination."""
    project_id = await get_first_project_id(client)

    dates = [date(2024, 5, 1 + i) for i in range(5)]
    await create_multiple_sessions(client, project_id, dates)

    # First page
    response = await client.get(
        "/api/sessions?min_date=2024-05-01&max_date=2024-05-06&page=1&page_size=2"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Second page
    response = await client.get(
        "/api/sessions?min_date=2024-05-01&max_date=2024-05-06&page=2&page_size=2"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_get_sessions_invalid_min_date(client: AsyncClient):
    """Test invalid min_date format returns 400."""
    response = await client.get("/api/sessions?min_date=invalid-date")

    # Should return 400 (not 422) due to our custom exception handler
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_sessions_invalid_max_date(client: AsyncClient):
    """Test invalid max_date format returns 400."""
    response = await client.get("/api/sessions?max_date=not-a-date")

    # Should return 400 (not 422) due to our custom exception handler
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_sessions_date_filter_boundary(client: AsyncClient):
    """Test boundary conditions for date filters (inclusive min, exclusive max)."""
    project_id = await get_first_project_id(client)

    boundary_date = date(2024, 6, 15)
    await create_session(client, project_id, boundary_date)

    # Test min_date with exact boundary (should be included - inclusive)
    response = await client.get(f"/api/sessions?min_date={boundary_date.isoformat()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    # Test max_date with exact boundary (should be excluded - exclusive)
    response = await client.get(f"/api/sessions?max_date={boundary_date.isoformat()}")
    assert response.status_code == 200
    data = response.json()
    for session in data["items"]:
        assert session["date"] != boundary_date.isoformat()


@pytest.mark.asyncio
async def test_get_sessions_filter_by_single_project(client: AsyncClient):
    """Test filtering sessions by a single project ID."""
    # Get first two projects
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 2, "Need at least 2 projects for this test"

    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]

    # Create 3 sessions for project 1
    for i in range(3):
        await create_session(client, project1_id, date(2024, 7, 1 + i), 30)

    # Create 2 sessions for project 2
    for i in range(2):
        await create_session(client, project2_id, date(2024, 7, 4 + i), 30)

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

    # Create sessions for each project
    await create_session(client, project1_id, date(2024, 8, 1))
    await create_session(client, project1_id, date(2024, 8, 2))
    await create_session(client, project2_id, date(2024, 8, 3))
    await create_session(client, project3_id, date(2024, 8, 4))

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
    await create_session(client, project1_id, date(2024, 9, 1))

    # Filter by project 2 (should return no results)
    response = await client.get(f"/api/sessions?project_id={project2_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_get_sessions_filter_by_project_with_date_filters(client: AsyncClient):
    """Test combining project_id filter with date filters."""
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    assert len(projects) >= 2, "Need at least 2 projects for this test"

    project1_id = projects[0]["id"]
    project2_id = projects[1]["id"]

    # Create sessions for project 1 at different dates
    await create_session(client, project1_id, date(2024, 10, 1))
    await create_session(client, project1_id, date(2024, 10, 6))

    # Create sessions for project 2 at different dates
    await create_session(client, project2_id, date(2024, 10, 3))
    await create_session(client, project2_id, date(2024, 10, 8))

    # Filter by project 1 with date range that only includes the second session
    response = await client.get(
        f"/api/sessions?project_id={project1_id}&min_date=2024-10-05&max_date=2024-10-07"
    )

    assert response.status_code == 200
    data = response.json()

    # Should only get 1 session (project 1, on 2024-10-06)
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["project_id"] == project1_id
    assert data["items"][0]["date"] == "2024-10-06"


@pytest.mark.asyncio
async def test_get_sessions_filter_by_project_with_pagination(client: AsyncClient):
    """Test filtering by project ID with pagination."""
    projects_response = await client.get("/api/projects")
    projects = projects_response.json()
    project_id = projects[0]["id"]

    dates = [date(2024, 11, 1 + i) for i in range(5)]
    await create_multiple_sessions(client, project_id, dates)

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

    # Create a session
    created_session = await create_session(client, project_id, date(2026, 6, 15), 60)
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

    # Create 3 sessions
    session1 = await create_session(client, project_id, date(2024, 12, 1), 60)
    session2 = await create_session(client, project_id, date(2024, 12, 2), 60)
    session3 = await create_session(client, project_id, date(2024, 12, 3), 60)

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

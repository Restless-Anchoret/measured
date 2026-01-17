"""
Integration tests for the sessions endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Test creating a new session."""
    # First, get a project ID
    projects_response = await client.get("/api/projects")
    project_id = projects_response.json()[0]["id"]
    
    # Create a session
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
    projects_response = await client.get("/api/projects")
    project_id = projects_response.json()[0]["id"]
    
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
    # Create multiple sessions
    projects_response = await client.get("/api/projects")
    project_id = projects_response.json()[0]["id"]
    
    # Create 5 sessions
    for i in range(5):
        start_time = datetime.now() - timedelta(hours=i+1)
        end_time = datetime.now() - timedelta(hours=i)
        session_data = {
            "project_id": project_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        await client.post("/api/sessions", json=session_data)
    
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
    
    # Verify sessions are ordered by created_at DESC (most recent first)
    all_sessions_response = await client.get("/api/sessions?page=1&page_size=100")
    all_sessions = all_sessions_response.json()["items"]
    created_at_times = [s["created_at"] for s in all_sessions]
    # Should be in descending order
    assert created_at_times == sorted(created_at_times, reverse=True)


@pytest.mark.asyncio
async def test_get_sessions_pagination_validation(client: AsyncClient):
    """Test pagination query parameter validation."""
    # Test invalid page (less than 1)
    response = await client.get("/api/sessions?page=0")
    assert response.status_code == 422
    
    # Test invalid page_size (less than 1)
    response = await client.get("/api/sessions?page_size=0")
    assert response.status_code == 422
    
    # Test page_size too large (greater than 100)
    response = await client.get("/api/sessions?page_size=101")
    assert response.status_code == 422
    
    # Test valid parameters
    response = await client.get("/api/sessions?page=1&page_size=50")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_session_by_id(client: AsyncClient):
    """Test getting a single session by ID."""
    # Create a session first
    projects_response = await client.get("/api/projects")
    project_id = projects_response.json()[0]["id"]
    
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now()
    session_data = {
        "project_id": project_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    create_response = await client.post("/api/sessions", json=session_data)
    created_session = create_response.json()
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
    # Create a session first
    projects_response = await client.get("/api/projects")
    project_id = projects_response.json()[0]["id"]
    
    start_time = datetime.now() - timedelta(hours=3)
    end_time = datetime.now() - timedelta(hours=2)
    session_data = {
        "project_id": project_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    create_response = await client.post("/api/sessions", json=session_data)
    session_id = create_response.json()["id"]
    
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
    assert updated_session["created_at"] == create_response.json()["created_at"]


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


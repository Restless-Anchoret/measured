"""
Integration tests for the projects endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_projects(client: AsyncClient):
    """Test getting all projects."""
    response = await client.get("/api/projects")
    
    assert response.status_code == 200
    projects = response.json()
    
    # Should have the seeded test projects
    assert isinstance(projects, list)
    assert len(projects) == 5
    
    # Check project structure
    for project in projects:
        assert "id" in project
        assert "name" in project
        assert isinstance(project["id"], int)
        assert isinstance(project["name"], str)
    
    # Check that projects are sorted by id
    project_ids = [p["id"] for p in projects]
    assert project_ids == sorted(project_ids)
    
    # Verify expected project names exist
    project_names = [p["name"] for p in projects]
    expected_names = ["Work", "Personal", "Learning", "Exercise", "Hobbies"]
    for name in expected_names:
        assert name in project_names


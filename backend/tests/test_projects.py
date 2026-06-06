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
        assert "color" in project
        assert "extraColor" in project
        assert isinstance(project["id"], int)
        assert isinstance(project["name"], str)
        assert isinstance(project["color"], str)
        # extraColor is optional, so it can be None or str
        assert project["extraColor"] is None or isinstance(project["extraColor"], str)

    # Check that projects are sorted by id
    project_ids = [p["id"] for p in projects]
    assert project_ids == sorted(project_ids)

    # Verify expected project names exist
    project_names = [p["name"] for p in projects]
    expected_names = ["Work", "Personal", "Learning", "Exercise", "Hobbies"]
    for name in expected_names:
        assert name in project_names


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    """Test creating a project with all fields."""
    payload = {"name": "New Project", "color": "#aabbcc", "extraColor": "#112233"}
    response = await client.post("/api/projects", json=payload)

    assert response.status_code == 201
    project = response.json()
    assert isinstance(project["id"], int)
    assert project["name"] == "New Project"
    assert project["color"] == "#aabbcc"
    assert project["extraColor"] == "#112233"


@pytest.mark.asyncio
async def test_create_project_without_extra_color(client: AsyncClient):
    """Test creating a project omitting the optional extraColor field."""
    payload = {"name": "Minimal Project", "color": "#ffffff"}
    response = await client.post("/api/projects", json=payload)

    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "Minimal Project"
    assert project["color"] == "#ffffff"
    assert project["extraColor"] is None


@pytest.mark.asyncio
async def test_create_project_appears_in_list(client: AsyncClient):
    """Test that a newly created project is returned by GET /api/projects."""
    payload = {"name": "Listed Project", "color": "#123456"}
    create_response = await client.post("/api/projects", json=payload)
    assert create_response.status_code == 201
    new_id = create_response.json()["id"]

    list_response = await client.get("/api/projects")
    assert list_response.status_code == 200
    project_ids = [p["id"] for p in list_response.json()]
    assert new_id in project_ids


@pytest.mark.asyncio
async def test_create_project_missing_name(client: AsyncClient):
    """Test that omitting name returns 400 (app maps validation errors to 400)."""
    response = await client.post("/api/projects", json={"color": "#aabbcc"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_project_missing_color(client: AsyncClient):
    """Test that omitting color returns 400 (app maps validation errors to 400)."""
    response = await client.post("/api/projects", json={"name": "No Color"})
    assert response.status_code == 400


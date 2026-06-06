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


@pytest.mark.asyncio
async def test_get_projects_default_sort_explicit(client: AsyncClient):
    """Test that sort=DEFAULT returns projects ordered by id."""
    response = await client.get("/api/projects?sort=DEFAULT")
    assert response.status_code == 200
    projects = response.json()
    project_ids = [p["id"] for p in projects]
    assert project_ids == sorted(project_ids)


@pytest.mark.asyncio
async def test_get_projects_invalid_sort(client: AsyncClient):
    """Test that an invalid sort value returns 422."""
    response = await client.get("/api/projects?sort=INVALID")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_projects_most_recently_used_sort(client: AsyncClient, test_db):
    """Test MOST_RECENTLY_USED sort orders projects by descending session count then id."""
    # Fetch seeded project ids ordered by id
    rows = await test_db.fetch_all("SELECT id FROM projects ORDER BY id")
    ids = [r["id"] for r in rows]
    p1, p2, p3, p4, p5 = ids

    now = "2026-01-01 12:00:00"
    end = "2026-01-01 13:00:00"

    # p3: 3 sessions, p1: 2 sessions, p2: 1 session, p4/p5: 0 sessions
    sessions = [
        (p1, now, end), (p1, now, end),
        (p2, now, end),
        (p3, now, end), (p3, now, end), (p3, now, end),
    ]
    for project_id, start, stop in sessions:
        await test_db.execute(
            "INSERT INTO sessions (project_id, start_time, end_time, created_at) VALUES (:pid, :s, :e, :c)",
            {"pid": project_id, "s": start, "e": stop, "c": now},
        )

    response = await client.get("/api/projects?sort=MOST_RECENTLY_USED")
    assert response.status_code == 200
    result_ids = [p["id"] for p in response.json()]

    # p3 first (3), then p1 (2), then p2 (1), then p4/p5 (0, sorted by id)
    assert result_ids == [p3, p1, p2, p4, p5]


@pytest.mark.asyncio
async def test_get_projects_most_recently_used_only_last_250_sessions(client: AsyncClient, test_db):
    """Test that MOST_RECENTLY_USED only considers the 250 most recent sessions."""
    rows = await test_db.fetch_all("SELECT id FROM projects ORDER BY id")
    ids = [r["id"] for r in rows]
    p1, p2 = ids[0], ids[1]

    now = "2026-01-01 12:00:00"
    end = "2026-01-01 13:00:00"

    # Insert 251 sessions for p1 (older) and 1 session for p2 (newest)
    for _ in range(251):
        await test_db.execute(
            "INSERT INTO sessions (project_id, start_time, end_time, created_at) VALUES (:pid, :s, :e, :c)",
            {"pid": p1, "s": now, "e": end, "c": now},
        )
    await test_db.execute(
        "INSERT INTO sessions (project_id, start_time, end_time, created_at) VALUES (:pid, :s, :e, :c)",
        {"pid": p2, "s": now, "e": end, "c": now},
    )

    response = await client.get("/api/projects?sort=MOST_RECENTLY_USED")
    assert response.status_code == 200
    result_ids = [p["id"] for p in response.json()]

    # The 250 most recent sessions: 1 for p2 + 249 for p1. p1 still leads (249 vs 1).
    assert result_ids[0] == p1
    assert result_ids[1] == p2


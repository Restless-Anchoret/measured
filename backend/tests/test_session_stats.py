"""
Integration tests for GET /api/sessions/stats.
"""
from httpx import AsyncClient

from app.routers.session_stats import PROJECT_ID_ORDER


async def add_session(client: AsyncClient, project_id: int, session_date: str, minutes: int):
    response = await client.post(
        "/api/sessions",
        json={"project_id": project_id, "date": session_date, "duration_minutes": minutes},
    )
    assert response.status_code == 201


async def get_stats(client: AsyncClient, **params):
    response = await client.get("/api/sessions/stats", params=params)
    return response


async def test_daily_stats_include_empty_segments(client: AsyncClient):
    await add_session(client, 1, "2025-01-02", 30)
    await add_session(client, 1, "2025-01-02", 15)
    await add_session(client, 2, "2025-01-02", 10)

    response = await get_stats(client, from_date="2025-01-01", to_date="2025-01-04", aggregation_by="day")
    assert response.status_code == 200
    data = response.json()

    assert [s["start"] for s in data["segments"]] == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert [s["end"] for s in data["segments"]] == ["2025-01-02", "2025-01-03", "2025-01-04"]
    assert data["segments"][0] == {"start": "2025-01-01", "end": "2025-01-02", "total_minutes": 0, "projects": []}
    assert data["segments"][1]["total_minutes"] == 55
    assert data["segments"][1]["projects"] == [
        {"project_id": 1, "duration_minutes": 45},
        {"project_id": 2, "duration_minutes": 10},
    ]
    assert data["total_minutes"] == 55
    assert data["session_count"] == 3


async def test_weekly_segments_start_on_monday(client: AsyncClient):
    # 2025-01-01 is a Wednesday; its week starts Monday 2024-12-30.
    await add_session(client, 1, "2024-12-29", 99)  # Sunday before: out of range, never counted
    await add_session(client, 1, "2025-01-01", 20)
    await add_session(client, 1, "2025-01-06", 40)  # next Monday

    response = await get_stats(client, from_date="2025-01-01", to_date="2025-01-08", aggregation_by="week")
    data = response.json()

    assert [(s["start"], s["end"]) for s in data["segments"]] == [
        ("2024-12-30", "2025-01-06"),
        ("2025-01-06", "2025-01-13"),
    ]
    assert [s["total_minutes"] for s in data["segments"]] == [20, 40]
    assert data["total_minutes"] == 60


async def test_monthly_segments(client: AsyncClient):
    await add_session(client, 1, "2025-01-31", 10)
    await add_session(client, 1, "2025-02-01", 20)
    await add_session(client, 2, "2025-03-15", 30)

    response = await get_stats(client, from_date="2025-01-01", to_date="2025-04-01", aggregation_by="month")
    data = response.json()

    assert [(s["start"], s["end"]) for s in data["segments"]] == [
        ("2025-01-01", "2025-02-01"),
        ("2025-02-01", "2025-03-01"),
        ("2025-03-01", "2025-04-01"),
    ]
    assert [s["total_minutes"] for s in data["segments"]] == [10, 20, 30]


async def test_to_date_is_exclusive(client: AsyncClient):
    await add_session(client, 1, "2025-01-03", 50)

    response = await get_stats(client, from_date="2025-01-01", to_date="2025-01-03", aggregation_by="day")
    data = response.json()

    assert len(data["segments"]) == 2
    assert data["total_minutes"] == 0
    assert data["session_count"] == 0


async def test_project_filter(client: AsyncClient):
    await add_session(client, 1, "2025-01-01", 10)
    await add_session(client, 2, "2025-01-01", 20)
    await add_session(client, 3, "2025-01-01", 30)

    response = await client.get(
        "/api/sessions/stats",
        params=[("from_date", "2025-01-01"), ("to_date", "2025-01-02"), ("project_id", 2), ("project_id", 3)],
    )
    data = response.json()

    assert data["total_minutes"] == 50
    assert {p["project_id"] for p in data["segments"][0]["projects"]} == {2, 3}


async def test_projects_follow_backend_display_order(client: AsyncClient):
    # Test projects have ids 1-5. Display order puts 5 before 3 and 4, and 1 and 2 first.
    assert PROJECT_ID_ORDER.index(5) < PROJECT_ID_ORDER.index(3) < PROJECT_ID_ORDER.index(4)
    for pid in (4, 3, 5, 2, 1):
        await add_session(client, pid, "2025-01-01", 10)

    response = await get_stats(client, from_date="2025-01-01", to_date="2025-01-02")
    ids = [p["project_id"] for p in response.json()["segments"][0]["projects"]]

    assert ids == [1, 2, 5, 3, 4]


async def test_invalid_range_returns_400(client: AsyncClient):
    response = await get_stats(client, from_date="2025-01-05", to_date="2025-01-05")
    assert response.status_code == 400


async def test_missing_params_return_400(client: AsyncClient):
    response = await get_stats(client, from_date="2025-01-01")
    assert response.status_code == 400


async def test_stats_route_not_shadowed_by_session_id(client: AsyncClient):
    response = await get_stats(client, from_date="2025-01-01", to_date="2025-01-02")
    assert response.status_code == 200

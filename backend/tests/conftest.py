"""
Pytest configuration and fixtures for integration tests.
"""
import asyncio
import os
import pytest
import databases
from typing import AsyncGenerator
from testcontainers.community.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport

# app.database requires DATABASE_URL to be set at import time, but its module-level
# `database` global is never actually used by these tests -- get_db is overridden per-test
# to yield a testcontainers-backed connection instead. This placeholder just satisfies the
# import; it's never connected to.
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost/unused")

from app.main import app
from app.database import init_db, get_db


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop, needed because postgres_container/postgres_url
    below are session-scoped async fixtures -- pytest-asyncio's default event loop
    is function-scoped, which can't host a fixture that outlives a single test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a real Postgres container for the whole test session."""
    with PostgresContainer("postgres:18") as pg:
        yield pg


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Bare connection URL for the container -- schema setup happens per-test in test_db."""
    # driver=None gives a bare postgresql:// URL (asyncpg-compatible),
    # not the postgresql+psycopg2:// default testcontainers builds for SQLAlchemy sync use.
    return postgres_container.get_connection_url(driver=None)


@pytest.fixture(scope="function")
async def test_db(postgres_url: str) -> AsyncGenerator[databases.Database, None]:
    """Provide a freshly-created schema for each test."""
    test_database = databases.Database(postgres_url)
    await test_database.connect()

    await init_db(test_database)
    await seed_test_projects(test_database)

    yield test_database

    # Drop the schema so the next test's init_db() starts from a clean database.
    await test_database.execute("DROP TABLE IF EXISTS sessions, sessions_legacy_data, projects CASCADE")
    await test_database.disconnect()


async def seed_test_projects(db: databases.Database):
    """Seed test database with initial projects."""
    test_projects = [
        {"name": "Work", "color": "#ff5733", "extra_color": "#c70039"},
        {"name": "Personal", "color": "#33ff57", "extra_color": None},
        {"name": "Learning", "color": "#3357ff", "extra_color": "#1d3a8f"},
        {"name": "Exercise", "color": "#f3ff33", "extra_color": None},
        {"name": "Hobbies", "color": "#ff33f3", "extra_color": "#8f1d8a"},
    ]
    for project in test_projects:
        await db.execute(
            "INSERT INTO projects (name, color, extra_color) VALUES (:name, :color, :extra_color)",
            {"name": project["name"], "color": project["color"], "extra_color": project["extra_color"]}
        )


@pytest.fixture(scope="function")
async def client(test_db: databases.Database) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""

    # Override the get_db dependency to use test database
    async def override_get_db() -> AsyncGenerator[databases.Database, None]:
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Clean up dependency override
    app.dependency_overrides.clear()

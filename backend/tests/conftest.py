"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
import databases
import os
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import database, init_db, get_db


# Use in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test_measured.db"


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[databases.Database, None]:
    """Create a test database and initialize it for each test."""
    # Create a new database instance for testing
    test_database = databases.Database(TEST_DATABASE_URL)
    
    # Connect and initialize using production schema
    await test_database.connect()
    await init_db(test_database)
    
    # Populate with test projects
    await seed_test_projects(test_database)
    
    yield test_database
    
    # Cleanup: drop all tables and disconnect
    await test_database.execute("DROP TABLE IF EXISTS sessions")
    await test_database.execute("DROP TABLE IF EXISTS projects")
    await test_database.disconnect()
    
    # Clean up test database file
    if os.path.exists("./test_measured.db"):
        os.remove("./test_measured.db")


async def seed_test_projects(db: databases.Database):
    """Seed test database with initial projects."""
    test_projects = ["Work", "Personal", "Learning", "Exercise", "Hobbies"]
    for project_name in test_projects:
        await db.execute(
            "INSERT OR IGNORE INTO projects (name) VALUES (:name)",
            {"name": project_name}
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


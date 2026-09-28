import databases
import os
from typing import AsyncGenerator

# Postgres-only: local dev via docker-compose, production via Fly secret, tests via testcontainers.
DATABASE_URL = os.environ["DATABASE_URL"]

# Create database instance
database = databases.Database(DATABASE_URL)


async def get_db() -> AsyncGenerator[databases.Database, None]:
    """Dependency for getting database connection"""
    yield database


async def init_db(db: databases.Database | None = None):
    """Initialize database tables.

    Args:
        db: Optional database instance. If not provided, uses the global database instance.
    """
    target_db = db if db is not None else database

    # Create projects table
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)

    # Create sessions table
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            project_id INTEGER NOT NULL,
            date DATE NOT NULL,
            duration_minutes INTEGER NOT NULL,
            create_time BIGINT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Dead archive table (see the sessions date/duration migration) -- not read or written by
    # any application code, kept only in case start_time/end_time are ever needed again.
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS sessions_legacy_data (
            id INTEGER NOT NULL,
            start_time TEXT,
            end_time TEXT
        )
    """)

import databases
import os
from typing import AsyncGenerator

# Database URL - supports SQLite, PostgreSQL, MySQL, etc.
# Default: local development uses ./measured.db
# Production (Fly.io): uses /data/measured.db (set via environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./measured.db")

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
    is_sqlite = str(target_db.url).startswith("sqlite")
    pk = "INTEGER PRIMARY KEY" if is_sqlite else "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS projects (
            id {pk},
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)

    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id {pk},
            project_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

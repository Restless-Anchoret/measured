import databases
import os
from typing import AsyncGenerator

# Database URL - supports SQLite, PostgreSQL, MySQL, etc.
# Default: local development uses ./measured.db
# Production (Fly.io): uses /data/measured.db (set via environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./measured.db")

# Create database instance
database = databases.Database(DATABASE_URL)


def is_sqlite_db(db: databases.Database) -> bool:
    """Whether the given database connection is SQLite (vs. Postgres)."""
    return str(db.url).startswith("sqlite")


async def get_db() -> AsyncGenerator[databases.Database, None]:
    """Dependency for getting database connection"""
    yield database


async def init_db(db: databases.Database | None = None):
    """Initialize database tables.

    Args:
        db: Optional database instance. If not provided, uses the global database instance.
    """
    target_db = db if db is not None else database
    is_sqlite = is_sqlite_db(target_db)
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
    date_type = "TEXT" if is_sqlite else "DATE"

    # Create projects table
    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS projects (
            id {pk},
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)

    # Create sessions table
    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id {pk},
            project_id INTEGER NOT NULL,
            date {date_type} NOT NULL,
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

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
    
    # Create projects table
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)
    
    # Create sessions table
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            create_time BIGINT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

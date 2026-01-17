import databases
import os
from typing import AsyncGenerator

# Database URL - supports SQLite, PostgreSQL, MySQL, etc.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./measured.db")

# Create database instance
database = databases.Database(DATABASE_URL)


async def get_db() -> AsyncGenerator[databases.Database, None]:
    """Dependency for getting database connection"""
    yield database


async def init_db():
    """Initialize database tables"""
    # Create projects table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Create sessions table
    # Using TIMESTAMP for cross-database compatibility
    # SQLite stores as TEXT but accepts TIMESTAMP type
    # PostgreSQL and MySQL use native TIMESTAMP/DATETIME types
    await database.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

"""
Script to initialize the database with hardcoded projects.
Run this once to populate the projects table.
"""
import asyncio
from app.database import database, init_db

# Hardcoded projects
PROJECTS = [
    "Work",
    "Personal",
    "Learning",
    "Exercise",
    "Hobbies"
]


async def init_projects():
    """Initialize projects in the database"""
    # Check if projects already exist
    total_row = await database.fetch_one("SELECT COUNT(*) as count FROM projects")
    existing_count = total_row["count"]
    
    if existing_count > 0:
        print("Projects already initialized. Skipping...")
        return
    
    # Create projects
    for project_name in PROJECTS:
        await database.execute(
            "INSERT INTO projects (name) VALUES (:name)",
            {"name": project_name}
        )
    
    print(f"Initialized {len(PROJECTS)} projects: {', '.join(PROJECTS)}")


async def main():
    """Initialize database tables and projects"""
    await database.connect()
    try:
        await init_db()
        await init_projects()
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

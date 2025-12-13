"""
Script to initialize the database with hardcoded projects.
Run this once to populate the projects table.
"""
from app.database import SessionLocal, engine, Base
from app import models

# Create tables
Base.metadata.create_all(bind=engine)

# Hardcoded projects
PROJECTS = [
    "Work",
    "Personal",
    "Learning",
    "Exercise",
    "Hobbies"
]

def init_projects():
    db = SessionLocal()
    try:
        # Check if projects already exist
        existing_count = db.query(models.Project).count()
        if existing_count > 0:
            print("Projects already initialized. Skipping...")
            return
        
        # Create projects
        for project_name in PROJECTS:
            project = models.Project(name=project_name)
            db.add(project)
        
        db.commit()
        print(f"Initialized {len(PROJECTS)} projects: {', '.join(PROJECTS)}")
    except Exception as e:
        db.rollback()
        print(f"Error initializing projects: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_projects()


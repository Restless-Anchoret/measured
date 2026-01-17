"""
Plain Python classes for mapping database rows to objects.
These are used for explicit result mapping from SQL queries.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    id: int
    name: str
    
    @classmethod
    def from_row(cls, row) -> "Project":
        """Create Project from database row"""
        return cls(id=row["id"], name=row["name"])


@dataclass
class Session:
    id: int
    project_id: int
    start_time: datetime
    end_time: Optional[datetime]
    created_at: datetime
    
    @classmethod
    def from_row(cls, row) -> "Session":
        """Create Session from database row"""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
        )

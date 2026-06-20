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
    color: str
    extraColor: Optional[str] = None
    
    @classmethod
    def from_row(cls, row) -> "Project":
        """Create Project from database row"""
        return cls(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            extraColor=row["extra_color"] if row["extra_color"] else None
        )


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
        def _to_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val)

        return cls(
            id=row["id"],
            project_id=row["project_id"],
            start_time=_to_dt(row["start_time"]),
            end_time=_to_dt(row["end_time"]),
            created_at=_to_dt(row["created_at"])
        )

"""
Plain Python classes for mapping database rows to objects.
These are used for explicit result mapping from SQL queries.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
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
    date: Optional[date]
    duration_minutes: Optional[int]
    create_time: Optional[datetime]

    @classmethod
    def from_row(cls, row) -> "Session":
        """Create Session from database row"""
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            date=row["date"] if isinstance(row["date"], date) else date.fromisoformat(row["date"]) if row["date"] else None,
            duration_minutes=row["duration_minutes"],
            create_time=datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=row["create_time"]) if row["create_time"] else None,
        )

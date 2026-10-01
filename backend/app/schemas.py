from pydantic import BaseModel, ConfigDict
from datetime import date as date_type
from typing import Optional
from enum import Enum


class ProjectSort(str, Enum):
    DEFAULT = "DEFAULT"
    MOST_RECENTLY_USED = "MOST_RECENTLY_USED"


class ProjectCreate(BaseModel):
    name: str
    color: str
    extraColor: Optional[str] = None


class ProjectBase(BaseModel):
    id: int
    name: str
    color: str
    extraColor: Optional[str] = None


class Project(ProjectBase):
    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    project_id: int
    date: date_type
    duration_minutes: int


class SessionUpdate(BaseModel):
    date: date_type
    duration_minutes: int


class Session(BaseModel):
    id: int
    project_id: int
    date: Optional[date_type] = None
    duration_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedSessions(BaseModel):
    items: list[Session]
    total: int
    page: int
    page_size: int



class StatsProjectDuration(BaseModel):
    project_id: int
    duration_minutes: int


class StatsSegment(BaseModel):
    start: date_type  # inclusive
    end: date_type  # exclusive
    total_minutes: int
    projects: list[StatsProjectDuration]  # ordered by the backend's project display order


class SessionStats(BaseModel):
    segments: list[StatsSegment]
    total_minutes: int
    session_count: int

from pydantic import BaseModel, ConfigDict
from datetime import datetime
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


class SessionBase(BaseModel):
    project_id: int
    start_time: datetime
    end_time: Optional[datetime] = None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    start_time: datetime
    end_time: datetime


class Session(SessionBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedSessions(BaseModel):
    items: list[Session]
    total: int
    page: int
    page_size: int


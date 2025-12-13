from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProjectBase(BaseModel):
    id: int
    name: str


class Project(ProjectBase):
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


class PaginatedSessions(BaseModel):
    items: list[Session]
    total: int
    page: int
    page_size: int


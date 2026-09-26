from pydantic import BaseModel, ConfigDict, model_validator
from datetime import date as date_type, datetime
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
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    date: Optional[date_type] = None
    duration_minutes: Optional[int] = None

    @model_validator(mode="after")
    def check_fields(self):
        has_new = self.date is not None and self.duration_minutes is not None
        has_old = self.start_time is not None and self.end_time is not None
        if not has_new and not has_old:
            raise ValueError("Provide either (date and duration_minutes) or (start_time and end_time)")
        return self


class SessionUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    date: Optional[date_type] = None
    duration_minutes: Optional[int] = None

    @model_validator(mode="after")
    def check_fields(self):
        has_new = self.date is not None and self.duration_minutes is not None
        has_old = self.start_time is not None and self.end_time is not None
        if not has_new and not has_old:
            raise ValueError("Provide either (date and duration_minutes) or (start_time and end_time)")
        return self


class Session(BaseModel):
    id: int
    project_id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    date: Optional[date_type] = None
    duration_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedSessions(BaseModel):
    items: list[Session]
    total: int
    page: int
    page_size: int


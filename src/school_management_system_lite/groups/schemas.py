from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GroupResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    academic_year: str
    grade_level: int


class GroupResponseDetailed(GroupResponseBase):
    max_capacity: int
    created_at: datetime


class CreateGroup(BaseModel):
    name: str = Field(min_length=2, max_length=10)
    academic_year: str = Field(max_length=10)
    grade_level: int
    max_capacity: int = Field(ge=10, le=35)


class UpdateGroup(BaseModel):
    name: str | None = Field(min_length=2, max_length=10, default=None)
    academic_year: str | None = Field(max_length=10, default=None)
    grade_level: int | None = None
    max_capacity: int | None = Field(ge=10, le=35, default=None)

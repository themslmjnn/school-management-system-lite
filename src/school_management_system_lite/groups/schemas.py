from datetime import datetime

from pydantic import BaseModel, Field

from school_management_system_lite.utils.base_schema import BaseSchema


class GroupResponseBase(BaseSchema):
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

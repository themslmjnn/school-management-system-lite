from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    code: str


class SubjectResponseDetailed(SubjectResponseBase):
    description: str | None
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime


class CreateSubject(BaseModel):
    name: str = Field(min_length=5, max_length=100)
    code: str = Field(min_length=3, max_length=20)
    description: str | None = Field(max_length=500, default=None)


class UpdateSubject(BaseModel):
    name: str | None = Field(min_length=5, max_length=100, default=None)
    code: str | None = Field(min_length=3, max_length=20, default=None)
    description: str | None = Field(max_length=500, default=None)

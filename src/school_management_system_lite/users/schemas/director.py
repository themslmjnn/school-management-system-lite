from pydantic import BaseModel, Field


class UserBaseFilters(BaseModel):
    first_name: str | None = Field(min_length=3, max_length=10, default=None)
    last_name: str | None = Field(min_length=3, max_length=10, default=None)
    phone_number: str | None = Field(min_length=3, max_length=10, default=None)

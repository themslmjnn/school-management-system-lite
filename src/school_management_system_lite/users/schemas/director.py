from pydantic import BaseModel, ConfigDict, Field

from school_management_system_lite.users.utils.enums import UserStatus


class UserResponseBaseDirector(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    middle_name: str | None
    phone_number: str
    status: UserStatus


class UserFiltersDirector(BaseModel):
    first_name: str | None = Field(min_length=3, max_length=10, default=None)
    last_name: str | None = Field(min_length=3, max_length=10, default=None)
    phone_number: str | None = Field(min_length=3, max_length=10, default=None)

from datetime import date, datetime

from pydantic import BaseModel, Field

from school_management_system_lite.users.utils.shared_schemas import UserResponseBase
from school_management_system_lite.utils.enums import UserRole, UserStatus


class UserResponseBaseAdmin(UserResponseBase):
    role: UserRole
    status: UserStatus


class UserResponseDetailedAdmin(UserResponseBase):
    date_of_birth: date
    address: str | None
    phone_number: str
    email: str
    created_at: datetime


class CreateUserAdmin(BaseModel):
    first_name: str = Field(min_length=3, max_length=30)
    last_name: str = Field(min_length=3, max_length=30)
    middle_name: str | None = Field(min_length=3, max_length=30, default=None)
    date_of_birth: date
    address: str | None = Field(max_length=150)
    phone_number: str = Field(max_length=20)
    email: str = Field(max_length=50)
    role: UserRole
    password: str = Field(min_length=8)

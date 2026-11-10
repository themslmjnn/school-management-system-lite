from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from school_management_system_lite.users.utils.shared_schemas import UserResponseBase
from school_management_system_lite.users.utils.validators import (
    validate_date_of_birth_non_student,
    validate_date_of_birth_student,
    validate_email,
    validate_first_name,
    validate_last_name,
    validate_middle_name,
    validate_phone_number,
)
from school_management_system_lite.utils.enums import UserRole, UserStatus


class UserResponseBaseAdmin(UserResponseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    middle_name: str | None
    role: UserRole
    status: UserStatus


class UserResponseDetailedAdmin(UserResponseBaseAdmin):
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
    address: str | None = Field(max_length=150, default=None)
    phone_number: str = Field(max_length=20)
    email: str = Field(max_length=50)
    role: Literal[UserRole.STUDENT, UserRole.TEACHER, UserRole.DIRECTOR]

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, first_name: str) -> str:
        return validate_first_name(first_name)

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, last_name: str) -> str:
        return validate_last_name(last_name)

    @field_validator("middle_name")
    @classmethod
    def _validate_middle_name(cls, middle_name: str | None) -> str | None:
        if middle_name is None:
            return None

        return validate_middle_name(middle_name)

    @field_validator("address")
    @classmethod
    def _normalise_address(cls, address: str | None) -> str | None:
        if address is None:
            return None

        return address.strip()

    @field_validator("phone_number")
    @classmethod
    def _validate_phone_number(cls, phone_number: str) -> str:
        return validate_phone_number(phone_number)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, email: str) -> str:
        return validate_email(email)

    @model_validator(mode="after")
    def _validate_birth_date(self) -> CreateUserAdmin:
        if self.role in [UserRole.TEACHER, UserRole.DIRECTOR]:
            validate_date_of_birth_non_student(self.date_of_birth)
        elif self.role == UserRole.STUDENT:
            validate_date_of_birth_student(self.date_of_birth)

        return self


class UpdateIdentityAdmin(BaseModel):
    first_name: str | None = Field(min_length=3, max_length=30, default=None)
    last_name: str | None = Field(min_length=3, max_length=30, default=None)
    middle_name: str | None = Field(min_length=3, max_length=30, default=None)
    address: str | None = Field(max_length=150, default=None)
    phone_number: str | None = Field(max_length=20, default=None)

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, first_name: str | None) -> str | None:
        if first_name is None:
            return None

        return validate_first_name(first_name)

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, last_name: str | None) -> str | None:
        if last_name is None:
            return None

        return validate_last_name(last_name)

    @field_validator("middle_name")
    @classmethod
    def _validate_middle_name(cls, middle_name: str | None) -> str | None:
        if middle_name is None:
            return None

        return validate_middle_name(middle_name)

    @field_validator("address")
    @classmethod
    def _normalise_address(cls, address: str | None) -> str | None:
        if address is None:
            return None

        return address.strip()

    @field_validator("phone_number")
    @classmethod
    def _validate_phone_number(cls, phone_number: str | None) -> str | None:
        if phone_number is None:
            return None

        return validate_phone_number(phone_number)


class UpdateEmailAdmin(BaseModel):
    email: str | None = Field(max_length=50, default=None)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, email: str | None) -> str | None:
        if email is None:
            return None

        return validate_email(email)

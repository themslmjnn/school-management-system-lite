from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from school_management_system_lite.users.utils import validators
from school_management_system_lite.users.utils.enums import UserRole, UserStatus


class UserResponseBaseAdmin(BaseModel):
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
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    middle_name: str | None = Field(max_length=50, default=None)
    role: Literal[UserRole.STUDENT, UserRole.TEACHER, UserRole.DIRECTOR]
    phone_number: str = Field(max_length=30)
    email: str = Field(max_length=50)
    date_of_birth: date
    address: str | None = Field(max_length=200, default=None)

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, first_name: str) -> str:
        return validators.validate_first_name(first_name)

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, last_name: str) -> str:
        return validators.validate_last_name(last_name)

    @field_validator("middle_name")
    @classmethod
    def _validate_middle_name(cls, middle_name: str | None) -> str | None:
        return (
            validators.validate_middle_name(middle_name)
            if middle_name is not None
            else None
        )

    @field_validator("phone_number")
    @classmethod
    def _validate_phone_number(cls, phone_number: str) -> str:
        return validators.validate_phone_number(phone_number)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, email: str) -> str:
        return validators.validate_email(email)

    @field_validator("date_of_birth")
    @classmethod
    def _validate_birth_date(cls, value: date, info: ValidationInfo) -> date:
        role = info.data.get("role")

        if role == UserRole.STUDENT:
            return validators.validate_date_of_birth_student(value)
        elif role in (UserRole.TEACHER, UserRole.DIRECTOR):
            return validators.validate_date_of_birth_non_student(value)

        return value

    @field_validator("address")
    @classmethod
    def _validate_address(cls, address: str | None) -> str | None:
        return validators.validate_address(address) if address is not None else None


class UpdateUserIdentityAdmin(BaseModel):
    first_name: str | None = Field(max_length=50, default=None)
    last_name: str | None = Field(max_length=50, default=None)
    middle_name: str | None = Field(max_length=50, default=None)
    phone_number: str | None = Field(max_length=30, default=None)
    address: str | None = Field(max_length=200, default=None)

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, first_name: str | None) -> str | None:
        return (
            validators.validate_first_name(first_name)
            if first_name is not None
            else None
        )

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, last_name: str | None) -> str | None:
        return (
            validators.validate_last_name(last_name) if last_name is not None else None
        )

    @field_validator("middle_name")
    @classmethod
    def _validate_middle_name(cls, middle_name: str | None) -> str | None:
        return (
            validators.validate_middle_name(middle_name)
            if middle_name is not None
            else None
        )

    @field_validator("phone_number")
    @classmethod
    def _validate_phone_number(cls, phone_number: str | None) -> str | None:
        return (
            validators.validate_phone_number(phone_number)
            if phone_number is not None
            else None
        )

    @field_validator("address")
    @classmethod
    def _validate_address(cls, address: str | None) -> str | None:
        return validators.validate_address(address) if address is not None else None

    @model_validator(mode="after")
    def validate_non_nullable_fields(self):
        non_nullable_fields = {"first_name", "last_name", "phone_number"}

        for field in non_nullable_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class UpdateUserEmailAdmin(BaseModel):
    email: str | None = Field(max_length=50, default=None)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, email: str | None) -> str | None:
        return validators.validate_email(email) if email is not None else None


class UserFiltersAdmin(BaseModel):
    first_name: str | None = Field(min_length=3, max_length=10, default=None)
    last_name: str | None = Field(min_length=3, max_length=10, default=None)
    phone_number: str | None = Field(min_length=3, max_length=10, default=None)
    email: str | None = Field(min_length=3, max_length=15, default=None)

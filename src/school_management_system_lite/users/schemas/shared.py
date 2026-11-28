from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from school_management_system_lite.users.utils.validators import (
    validate_email,
    validate_password,
)


class UserSelfResponseDetailed(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    middle_name: str | None
    date_of_birth: date
    address: str | None
    phone_number: str
    email: str
    created_at: datetime


class UpdateMyEmail(BaseModel):
    new_email: str | None = Field(max_length=50, default=None)

    @field_validator("new_email")
    @classmethod
    def _validate_email(cls, new_email: str | None) -> str | None:
        return validate_email(new_email) if new_email is not None else None


class UpdateMyPassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return validate_password(v)

    @model_validator(mode="after")
    def _validate_passwords_differ(self) -> "UpdateMyPassword":
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from current password")

        return self

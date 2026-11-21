from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from school_management_system_lite.users.utils.validators import validate_email


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


class UpdateEmailMe(BaseModel):
    new_email: str | None = Field(max_length=50, default=None)

    @field_validator("new_email")
    @classmethod
    def _validate_email(cls, new_email: str | None) -> str | None:
        return validate_email(new_email) if new_email is not None else None

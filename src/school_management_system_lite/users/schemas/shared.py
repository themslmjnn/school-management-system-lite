from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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

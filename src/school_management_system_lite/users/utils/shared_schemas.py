from school_management_system_lite.utils.base_schema import BaseSchema


class UserResponseBase(BaseSchema):
    id: int
    first_name: str
    last_name: str
    middle_name: str | None

from enum import StrEnum


class UserRole(StrEnum):
    SYSTEM_ADMIN = "system_admin"
    DIRECTOR = "director"
    TEACHER = "teacher"
    STUDENT = "student"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_ACTIVATION = "pending_activation"
    EXPELLED = "expelled"
    WITHDRAWN = "withdrawn"
    GRADUATED = "graduated"


class UserSortField(StrEnum):
    CREATED_AT = "created_at"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    STATUS = "status"

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


class OrderBy(StrEnum):
    ASC = "asc"
    DESC = "desc"

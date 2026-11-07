from fastapi import status
from sqlalchemy.exc import IntegrityError

from school_management_system_lite.core.exceptions import AppException


class GroupAlreadyExists(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Group with this name and academic year already exists"
    error_code = "GROUP_ALREADY_EXISTS"


def handle_duplicate_group_integrity_error(exc: IntegrityError) -> None:
    if "uq_groups_name_academic_year" in str(exc.orig):
        raise GroupAlreadyExists()

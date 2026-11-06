from fastapi import status
from sqlalchemy.exc import IntegrityError

from school_management_system_lite.core.exceptions import AppException


# HTTP404
class SubjectNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Subject not found"
    error_code = "SUBJECT_NOT_FOUND"


# HTTP409
class SubjectCodeAlreadyTakenError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Subject with this code already exists"
    error_code = "SUBJECT_CODE_ALREADY_TAKEN"


def handle_subject_code_integrity_error(exc: IntegrityError) -> None:
    if "uq_subjects_code" in str(exc.orig):
        raise SubjectCodeAlreadyTakenError()

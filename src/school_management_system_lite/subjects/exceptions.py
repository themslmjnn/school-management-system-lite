from fastapi import status

from school_management_system_lite.core.exceptions import AppException


class SubjectCodeAlreadyTaken(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Subject with this code already exists"
    error_code = "SUBJECT_CODE_ALREADY_TAKEN"


def handle_subject_code_integrity_error(exc: InterruptedError) -> None:
    if "uq_subjects_code" in str(exc.orig):
        raise SubjectCodeAlreadyTaken()

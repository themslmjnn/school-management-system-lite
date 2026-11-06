from fastapi import status
from sqlalchemy.exc import IntegrityError

from school_management_system_lite.core.exceptions import AppException


# HTTP404
class UserNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "User not found"
    error_code = "USER_NOT_FOUND"


# HTTP409
class PhoneNumberAlreadyTakenError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Phone number already taken"
    error_code = "PHONE_NUMBER_ALREADY_TAKEN"


class EmailAlreadyTakenError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Email already taken"
    error_code = "EMAIL_ALREADY_TAKEN"


# EXCEPTION HANDLERS
def handle_phone_number_integrity_error(exc: IntegrityError) -> None:
    if "uq_users_phone_number" in str(exc.orig):
        raise PhoneNumberAlreadyTakenError()


def handle_email_integrity_error(exc: IntegrityError) -> None:
    if "uq_users_email" in str(exc.orig):
        raise EmailAlreadyTakenError()

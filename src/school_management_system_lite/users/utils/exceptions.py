from fastapi import status
from sqlalchemy.exc import IntegrityError

from school_management_system_lite.core.exceptions.handlers import AppException


# HTTP404
class UserNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "User not found"
    error_code = "USER_NOT_FOUND"


# HTTP409
class PhoneNumberAlreadyTakenError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Phone number is already taken"
    error_code = "PHONE_NUMBER_ALREADY_TAKEN"


class EmailAlreadyTakenError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Email is already taken"
    error_code = "EMAIL_ALREADY_TAKEN"


class UserAlreadyInactiveError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "User is already inactive"
    error_code = "USER_ALREADY_INACTIVE"


class UserAlreadyActiveError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "User is already active"
    error_code = "USER_ALREADY_ACTIVE"


class UserPendingActivationError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "User status is pending activation"
    error_code = "USER_PENDING_ACTIVATION"


class PasswordResetAlreadyRequestedError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "User already has pending password reset requests"
    error_code = "PASSWORD_RESET_ALREADY_REQUESTED"


# EXCEPTION HANDLERS
def handle_phone_number_integrity_error(exc: IntegrityError) -> None:
    if "uq_users_phone_number" in str(exc.orig) or "users.phone_number" in str(
        exc.orig
    ):
        raise PhoneNumberAlreadyTakenError()


def handle_email_integrity_error(exc: IntegrityError) -> None:
    if "uq_users_email" in str(exc.orig) or "users.email" in str(exc.orig):
        raise EmailAlreadyTakenError()

from fastapi import status

from school_management_system_lite.core.exceptions import AppException


class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid credentials"
    error_code = "INVALID_CREDENTIALS"


class AccountNotActivatedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account not activated"
    error_code = "ACCOUNT_NOT_ACTIVATED"

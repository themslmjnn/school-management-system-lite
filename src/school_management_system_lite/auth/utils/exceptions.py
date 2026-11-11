from fastapi import status

from school_management_system_lite.core.exceptions.handlers import AppException


# HTTP401
class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid credentials"
    error_code = "INVALID_CREDENTIALS"


class InvalidAccessTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid access token"
    error_code = "INVALID_ACCESS_TOKEN"


class ExpiredAccessTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Expired access token"
    error_code = "EXPIRED_ACCESS_TOKEN"


class UserNotActivatedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account is not activated"
    error_code = "ACCOUNT_NOT_ACTIVATED"


class UserInactiveError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account is inactive"
    error_code = "ACCOUNT_INACTIVE"

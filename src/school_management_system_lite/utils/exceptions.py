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


class InvalidAccessTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid access token"
    error_code = "INVALID_ACCESS_TOKEN"


class ExpiredAccessTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Expired access token"
    error_code = "EXPIRED_ACCESS_TOKEN"


class AccountNotActiveError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account inactive"
    error_code = "ACCOUNT_INACTIVE"


class AccountInactiveError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account inactive"
    error_code = "ACCOUNT_INACTIVE"


class AccountGraduatedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account graduated"
    error_code = "ACCOUNT_GRADUATED"


class AccountExpelledError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account expelled"
    error_code = "ACCOUNT_EXPELLED"


class AccountWithdrawnError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Account withdrawn"
    error_code = "ACCOUNT_WITHDRAWN"


class AccessDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Access denied"
    error_code = "ACCESS_DENIED"

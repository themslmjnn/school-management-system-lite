from fastapi import status

from school_management_system_lite.core.exceptions.exceptions import AppException


class AccessDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Access denied"
    error_code = "ACCESS_DENIED"

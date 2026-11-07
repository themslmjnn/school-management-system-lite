from fastapi import Response

from school_management_system_lite.core.config import Settings


def set_refresh_token_cookie(
    response: Response, raw_refresh_token: str, settings: Settings
) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=settings.COOKIE_SECURE,
        path="/auth/refresh-token",
    )


def delete_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/auth/refresh-token")

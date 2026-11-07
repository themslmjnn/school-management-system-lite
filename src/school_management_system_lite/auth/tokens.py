from datetime import UTC, datetime, timedelta

import jwt

from school_management_system_lite.core.config import Settings
from school_management_system_lite.core.security import sha256
from school_management_system_lite.utils.enums import UserRole
from school_management_system_lite.utils.exceptions import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
)


def create_access_token(
    *,
    user_id: int,
    role: UserRole,
    access_token_version: int,
    session_id: int,
    settings: Settings,
) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "atv": access_token_version,
        "session_id": session_id,
        "type": "access",
        "exp": datetime.now(UTC)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES),
    }

    return jwt.encode(
        payload=payload,
        key=settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(access_token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(
            jwt=access_token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "atv", "session_id", "exp"]},
        )

        if payload.get("type") != "access":
            raise InvalidAccessTokenError()

    except jwt.ExpiredSignatureError:
        raise ExpiredAccessTokenError()

    except jwt.InvalidTokenError:
        raise InvalidAccessTokenError()

    return payload


def create_refresh_token(
    *,
    user_id: int,
    session_id: int,
    settings: Settings,
) -> tuple[str, str]:
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS),
    }

    raw_refresh_token = jwt.encode(
        payload=payload,
        key=settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    return raw_refresh_token, sha256(raw_refresh_token)

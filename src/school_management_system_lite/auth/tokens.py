from datetime import UTC, datetime, timedelta

import jwt

from school_management_system_lite.core.config import Settings
from school_management_system_lite.core.security import sha256
from school_management_system_lite.utils.enums import UserRole


def create_access_token(
    *,
    user_id: int,
    role: UserRole,
    access_token_version: int,
    settings: Settings,
) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "atv": str(access_token_version),
        "type": "access",
        "exp": datetime.now(UTC)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES),
    }

    return jwt.encode(
        payload=payload,
        key=settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


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

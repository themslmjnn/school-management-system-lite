import hashlib
import hmac
import secrets

import bcrypt
from fastapi.concurrency import run_in_threadpool

_BCRYPT_MAX_BYTES = 72

_DUMMY_HASH = bcrypt.hashpw(
    secrets.token_urlsafe(16).encode(), bcrypt.gensalt()
).decode()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash_password_sync(password: str) -> str:
    encoded_password = password.encode()
    if len(encoded_password) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {_BCRYPT_MAX_BYTES} bytes")

    return bcrypt.hashpw(encoded_password, bcrypt.gensalt()).decode()


def _verify_password_sync(plain_password: str, hashed_password: str | None) -> bool:
    encoded_plain_password = plain_password.encode()
    is_plain_password_too_long = len(encoded_plain_password) > _BCRYPT_MAX_BYTES
    target_hashed_password = hashed_password or _DUMMY_HASH

    try:
        are_passwords_matched = bcrypt.checkpw(
            encoded_plain_password[:_BCRYPT_MAX_BYTES], target_hashed_password.encode()
        )

    except ValueError:
        return False

    return (
        are_passwords_matched
        and not is_plain_password_too_long
        and hashed_password is not None
    )


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_hash_password_sync, password)


async def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    return await run_in_threadpool(
        _verify_password_sync, plain_password, hashed_password
    )


def generate_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)

    return raw_token, sha256(raw_token)


def verify_token(raw_token: str, hashed_token: str) -> bool:
    return hmac.compare_digest(sha256(raw_token), hashed_token)

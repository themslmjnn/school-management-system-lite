import hashlib
import hmac
import secrets

from passlib.context import CryptContext

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    hashed_password = hashed_password or hash_password("StrongPassword_123")

    return bcrypt_context.verify(plain_password, hashed_password)


def generate_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)

    return raw_token, sha256(raw_token)


def verify_token(raw_token: str, hashed_token: str) -> bool:
    return hmac.compare_digest(sha256(raw_token), hashed_token)

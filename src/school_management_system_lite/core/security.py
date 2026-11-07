import hashlib

from passlib.context import CryptContext

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    hashed_password = hashed_password or hash_password("StrongPassword_123")

    return bcrypt_context.verify(plain_password, hashed_password)

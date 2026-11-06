from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.security import hash_password
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.utils.exceptions import (
    handle_email_integrity_error,
    handle_phone_number_integrity_error,
)
from school_management_system_lite.utils.enums import UserStatus


class UserServiceAdmin:
    @staticmethod
    async def register_user(
        db_session: AsyncSession,
        payload: CreateUserAdmin,
    ) -> User:
        try:
            new_user = User(
                first_name=payload.first_name,
                last_name=payload.last_name,
                middle_name=payload.middle_name,
                date_of_birth=payload.date_of_birth,
                address=payload.address,
                phone_number=payload.phone_number,
                email=payload.email,
                role=payload.role,
                status=UserStatus.ACTIVE,
                password_hash=hash_password(payload.password),
            )

            db_session.add(new_user)
            await db_session.commit()
            await db_session.refresh(new_user)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_phone_number_integrity_error(exc)
            handle_email_integrity_error(exc)

            raise

        return new_user

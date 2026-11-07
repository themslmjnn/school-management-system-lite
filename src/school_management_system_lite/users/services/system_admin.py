from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.core.security import hash_password
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.repositories.system_admin import (
    UserRepositoryAdmin,
)
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UpdateUserAdmin,
)
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyActive,
    UserAlreadyInactive,
    UserNotFoundError,
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
            user = User(
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

            db_session.add(user)
            await db_session.flush()

            db_session.add(UserSession(user_id=user.id))

            await db_session.commit()
            await db_session.refresh(user)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_phone_number_integrity_error(exc)
            handle_email_integrity_error(exc)

            raise

        return user

    @staticmethod
    async def update_user(
        db_session: AsyncSession, user_id: int, payload: UpdateUserAdmin
    ) -> User:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        try:
            for field, value in payload.model_dump(exclude_unset=True).items():
                if field == "password":
                    user.password_hash = hash_password(value)

                setattr(user, field, value)

            await db_session.commit()
            await db_session.refresh(user)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_phone_number_integrity_error(exc)
            handle_email_integrity_error(exc)

            raise

        return user

    @staticmethod
    async def deactivate_user(db_session: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.INACTIVE:
            raise UserAlreadyInactive()

        user.status = UserStatus.INACTIVE

        await db_session.commit()

    @staticmethod
    async def activate_user(db_session: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.ACTIVE:
            raise UserAlreadyActive()

        user.status = UserStatus.ACTIVE

        await db_session.commit()

    @staticmethod
    async def get_users(db_session: AsyncSession) -> Sequence[User]:
        return await UserRepositoryAdmin.get_users(db_session)

    @staticmethod
    async def get_user(db_session: AsyncSession, user_id: int) -> User:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        return user

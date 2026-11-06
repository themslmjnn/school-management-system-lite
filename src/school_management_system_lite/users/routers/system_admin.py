from fastapi import APIRouter, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UserResponseDetailedAdmin,
)
from school_management_system_lite.users.services.system_admin import UserServiceAdmin

router = APIRouter(
    prefix="/admin/users",
    tags=["Users - System Admin"],
)


@router.post(
    "", response_model=UserResponseDetailedAdmin, status_code=status.HTTP_201_CREATED
)
async def register_user(
    db_session: db_session_dependency,
    payload: CreateUserAdmin,
):
    return await UserServiceAdmin.register_user(db_session, payload)

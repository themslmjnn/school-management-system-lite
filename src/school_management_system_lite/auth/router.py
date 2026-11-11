from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from school_management_system_lite.auth import service as auth_service
from school_management_system_lite.auth.schemas import LoginResponse
from school_management_system_lite.core.dependencies.auth import db_session_dependency

router = APIRouter(tags=["Auth"])


@router.post(
    "/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK
)
async def login(
    request: Request,
    response: Response,
    db_session: db_session_dependency,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    return await auth_service.login(
        request,
        response,
        db_session,
        form_data=form_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

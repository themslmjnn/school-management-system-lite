from typing import Annotated

from fastapi import Depends, Request
from httpx import AsyncClient


def get_resend_client(request: Request) -> AsyncClient | None:
    return request.app.state.resend_client


resend_client_dep = Annotated[AsyncClient | None, Depends(get_resend_client)]

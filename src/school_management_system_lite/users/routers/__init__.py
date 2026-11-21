from fastapi import APIRouter

from school_management_system_lite.users.routers.director import (
    router as director_router,
)
from school_management_system_lite.users.routers.system_admin import (
    router as system_admin_router,
)

router = APIRouter()

router.include_router(system_admin_router)
router.include_router(director_router)

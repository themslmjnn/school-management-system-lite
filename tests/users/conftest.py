import pytest

from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.utils.enums import UserRole


@pytest.fixture
def valid_user_payload():
    return CreateUserAdmin(
        first_name="Valid-first-name",
        last_name="Valid-last-name",
        date_of_birth="2008-05-01",
        address="valid_address",
        phone_number="+992222111222",
        email="valid_student_email@gmail.com",
        role=UserRole.STUDENT,
    )

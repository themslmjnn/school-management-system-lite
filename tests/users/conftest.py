from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_send_admin_identity_override_email(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.system_admin.send_admin_identity_override_email",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_send_admin_account_activation_email(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.system_admin.send_admin_account_activation_email",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_users_get_cache_system_admin(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.system_admin.get_cache",
        new_callable=AsyncMock,
        return_value=None,
    )


@pytest.fixture
def mock_users_delete_cache_system_admin(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.system_admin.delete_cache",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_users_set_cache_system_admin(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.system_admin.set_cache",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_user_base_repository_get_user_by_id_shared(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.shared.user_base_repository.get_by_id",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_users_get_cache_shared(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.shared.get_cache",
        new_callable=AsyncMock,
        return_value=None,
    )


@pytest.fixture
def mock_users_set_cache_shared(mocker):
    return mocker.patch(
        "school_management_system_lite.users.services.shared.set_cache",
        new_callable=AsyncMock,
    )

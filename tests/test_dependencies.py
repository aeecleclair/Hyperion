import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import is_user
from tests.commons import (
    create_user_with_groups,
)

admin_user: models_users.CoreUser
user_with_needed_account_type: models_users.CoreUser
user_with_restricted_account_type: models_users.CoreUser
user_external: models_users.CoreUser
user_with_restricted_group: models_users.CoreUser
user_with_needed_group: models_users.CoreUser


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global \
        admin_user, \
        user_with_restricted_account_type, \
        user_with_needed_account_type, \
        user_external, \
        user_with_restricted_group, \
        user_with_needed_group

    admin_user = await create_user_with_groups(
        [GroupType.admin],
    )
    user_with_restricted_account_type = await create_user_with_groups(
        [],
        AccountType.staff,
    )
    user_with_needed_account_type = await create_user_with_groups([], AccountType.demo)

    user_external = await create_user_with_groups(
        [],
        AccountType.external,
    )

    user_with_restricted_group = await create_user_with_groups(
        [GroupType.amap],
    )

    user_with_needed_group = await create_user_with_groups([GroupType.eclair])


def test_exclude_access_on_group(
    client: TestClient,
) -> None:
    user = is_user(
        excluded_groups=[GroupType.amap],
    )(admin_user)
    assert user == admin_user
    user = is_user(
        excluded_groups=[GroupType.amap],
    )(user_external)
    assert user == user_external
    user = is_user(
        excluded_groups=[GroupType.amap],
    )(user_with_restricted_account_type)
    assert user == user_with_restricted_account_type
    user = is_user(
        excluded_groups=[GroupType.amap],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = is_user(
        excluded_groups=[GroupType.amap],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is a member of any of the groups ",
    ):
        is_user(
            excluded_groups=[GroupType.amap],
        )(user_with_restricted_group)


def test_restrict_access_on_group(
    client: TestClient,
) -> None:
    user = is_user(
        included_groups=[GroupType.eclair],
    )(admin_user)
    assert user == admin_user
    user = is_user(
        included_groups=[GroupType.eclair],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        is_user(
            included_groups=[GroupType.eclair],
        )(user_with_restricted_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        is_user(
            included_groups=[GroupType.eclair],
        )(user_external)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        is_user(
            included_groups=[GroupType.eclair],
        )(user_with_needed_account_type)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        is_user(
            included_groups=[GroupType.eclair],
        )(user_with_restricted_account_type)


def test_restrict_access_on_account_type(
    client: TestClient,
) -> None:
    user = is_user(
        included_account_types=[AccountType.demo],
    )(admin_user)
    assert user == admin_user
    user = is_user(
        included_account_types=[AccountType.demo],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        is_user(
            included_account_types=[AccountType.demo],
        )(user_with_restricted_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        is_user(
            included_account_types=[AccountType.demo],
        )(user_external)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        is_user(
            included_account_types=[AccountType.demo],
        )(user_with_needed_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        is_user(
            included_account_types=[AccountType.demo],
        )(user_with_restricted_account_type)


def test_exclude_access_on_account_type(
    client: TestClient,
) -> None:
    user = is_user(
        excluded_account_types=[AccountType.staff],
    )(admin_user)
    assert user == admin_user
    user = is_user(
        excluded_account_types=[AccountType.staff],
    )(user_external)
    assert user == user_external
    user = is_user(
        excluded_account_types=[AccountType.staff],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = is_user(
        excluded_account_types=[AccountType.staff],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    user = is_user(
        excluded_account_types=[AccountType.staff],
    )(user_with_restricted_group)
    assert user == user_with_restricted_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        is_user(
            excluded_account_types=[AccountType.staff],
        )(user_with_restricted_account_type)


def test_exclude_access_on_external(
    client: TestClient,
) -> None:
    user = is_user(
        exclude_external=True,
    )(admin_user)
    assert user == admin_user
    user = is_user(
        exclude_external=True,
    )(user_with_restricted_account_type)
    assert user == user_with_restricted_account_type
    user = is_user(
        exclude_external=True,
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = is_user(
        exclude_external=True,
    )(user_with_needed_group)
    assert user == user_with_needed_group
    user = is_user(
        exclude_external=True,
    )(user_with_restricted_group)
    assert user == user_with_restricted_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is an external user",
    ):
        is_user(
            exclude_external=True,
        )(user_external)

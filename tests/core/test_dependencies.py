import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

import app.core.auth.dependencies_auth
from app import dependencies
from app.core.auth.dependencies_auth import (
    PERMISSION_CACHE_TTL,
    filter_user_token,
    get_cached_permission_requirements,
)
from app.core.auth.schemas_auth import FunctionalTokenData
from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.core.utils.config import Settings
from app.modules.mypayment.endpoints_mypayment import MyPaymentPermissions
from tests import commons
from tests.commons import (
    create_groups_with_permissions,
    create_user_with_groups,
    get_TestingSessionLocal,
)

group1: models_groups.CoreGroup
group2: models_groups.CoreGroup

admin_user: FunctionalTokenData
user_with_needed_account_type: FunctionalTokenData
user_with_restricted_account_type: FunctionalTokenData
user_external: FunctionalTokenData
user_with_restricted_group: FunctionalTokenData
user_with_needed_group: FunctionalTokenData


def construct_token_data_from_user(
    user: models_users.CoreUser,
    settings: Settings,
) -> FunctionalTokenData:
    return FunctionalTokenData(
        sub=user.id,
        group_ids=[str(group.id) for group in user.groups],
        account_type=user.account_type,
        school_id=user.school_id,
        settings=settings,
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    settings = commons.SETTINGS

    global \
        group1, \
        group2, \
        admin_user, \
        user_with_restricted_account_type, \
        user_with_needed_account_type, \
        user_external, \
        user_with_restricted_group, \
        user_with_needed_group

    group1 = await create_groups_with_permissions(
        [MyPaymentPermissions.access_payment],
        "random group",
    )
    group2 = await create_groups_with_permissions(
        [MyPaymentPermissions.access_payment],
        "random group2",
    )

    admin_user = construct_token_data_from_user(
        await create_user_with_groups(
            [GroupType.admin],
        ),
        settings,
    )
    user_with_restricted_account_type = construct_token_data_from_user(
        await create_user_with_groups(
            [],
            AccountType.staff,
        ),
        settings,
    )
    user_with_needed_account_type = construct_token_data_from_user(
        await create_user_with_groups([], AccountType.demo),
        settings,
    )

    user_external = construct_token_data_from_user(
        await create_user_with_groups(
            [],
            AccountType.external,
        ),
        settings,
    )

    user_with_restricted_group = construct_token_data_from_user(
        await create_user_with_groups(
            [group1.id],
        ),
        settings,
    )

    user_with_needed_group = construct_token_data_from_user(
        await create_user_with_groups([group2.id]),
        settings,
    )


def test_exclude_access_on_group() -> None:
    user = filter_user_token(
        excluded_groups=[group1.id],
    )(admin_user)
    assert user == admin_user
    user = filter_user_token(
        excluded_groups=[group1.id],
    )(user_external)
    assert user == user_external
    user = filter_user_token(
        excluded_groups=[group1.id],
    )(user_with_restricted_account_type)
    assert user == user_with_restricted_account_type
    user = filter_user_token(
        excluded_groups=[group1.id],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = filter_user_token(
        excluded_groups=[group1.id],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is a member of any of the groups ",
    ):
        filter_user_token(
            excluded_groups=[group1.id],
        )(user_with_restricted_group)


def test_restrict_access_on_group(
    client: TestClient,
) -> None:
    user = filter_user_token(
        included_groups=[group2.id],
    )(admin_user)
    assert user == admin_user
    user = filter_user_token(
        included_groups=[group2.id],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        filter_user_token(
            included_groups=[group2.id],
        )(user_with_restricted_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        filter_user_token(
            included_groups=[group2.id],
        )(user_external)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        filter_user_token(
            included_groups=[group2.id],
        )(user_with_needed_account_type)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is not a member of an allowed group",
    ):
        filter_user_token(
            included_groups=[group2.id],
        )(user_with_restricted_account_type)


def test_restrict_access_on_account_type(
    client: TestClient,
) -> None:
    user = filter_user_token(
        included_account_types=[AccountType.demo],
    )(admin_user)
    assert user == admin_user
    user = filter_user_token(
        included_account_types=[AccountType.demo],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        filter_user_token(
            included_account_types=[AccountType.demo],
        )(user_with_restricted_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        filter_user_token(
            included_account_types=[AccountType.demo],
        )(user_external)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        filter_user_token(
            included_account_types=[AccountType.demo],
        )(user_with_needed_group)
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        filter_user_token(
            included_account_types=[AccountType.demo],
        )(user_with_restricted_account_type)


def test_exclude_access_on_account_type(
    client: TestClient,
) -> None:
    user = filter_user_token(
        excluded_account_types=[AccountType.staff],
    )(admin_user)
    assert user == admin_user
    user = filter_user_token(
        excluded_account_types=[AccountType.staff],
    )(user_external)
    assert user == user_external
    user = filter_user_token(
        excluded_account_types=[AccountType.staff],
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = filter_user_token(
        excluded_account_types=[AccountType.staff],
    )(user_with_needed_group)
    assert user == user_with_needed_group
    user = filter_user_token(
        excluded_account_types=[AccountType.staff],
    )(user_with_restricted_group)
    assert user == user_with_restricted_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user account type is not allowed",
    ):
        filter_user_token(
            excluded_account_types=[AccountType.staff],
        )(user_with_restricted_account_type)


def test_exclude_access_on_external(
    client: TestClient,
) -> None:
    user = filter_user_token(
        exclude_external=True,
    )(admin_user)
    assert user == admin_user
    user = filter_user_token(
        exclude_external=True,
    )(user_with_restricted_account_type)
    assert user == user_with_restricted_account_type
    user = filter_user_token(
        exclude_external=True,
    )(user_with_needed_account_type)
    assert user == user_with_needed_account_type
    user = filter_user_token(
        exclude_external=True,
    )(user_with_needed_group)
    assert user == user_with_needed_group
    user = filter_user_token(
        exclude_external=True,
    )(user_with_restricted_group)
    assert user == user_with_restricted_group
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is an external user",
    ):
        filter_user_token(
            exclude_external=True,
        )(user_external)


async def test_permission_caching(client: TestClient, mocker: MockerFixture) -> None:

    initial_ENABLE_REDIS_CACHE = commons.SETTINGS.ENABLE_REDIS_CACHE
    commons.SETTINGS.ENABLE_REDIS_CACHE = True

    redis_client = dependencies.GLOBAL_STATE["redis_client"]
    if redis_client is None:
        pytest.fail("No Redis available for this test")
    spy_get = mocker.spy(redis_client, "get")
    spy_set = mocker.spy(redis_client, "set")
    spy_cruds = mocker.spy(
        app.core.auth.dependencies_auth,
        "get_permissions_by_permission_name",
    )
    key = f"core:permissions:{MyPaymentPermissions.access_payment}"

    redis_client.delete(key)

    async with get_TestingSessionLocal()() as db:
        group_ids, account_types = await get_cached_permission_requirements(
            MyPaymentPermissions.access_payment,
            db,
            commons.SETTINGS,
            redis_client,
        )
    spy_get.assert_called_once_with(key)
    spy_cruds.assert_called_once_with(
        db,
        MyPaymentPermissions.access_payment,
    )
    spy_set.assert_called_once_with(
        key,
        json.dumps(
            {
                "groups": group_ids,
                "account_types": [account_type.value for account_type in account_types],
            },
        ),
        ex=PERMISSION_CACHE_TTL,
    )
    spy_get.reset_mock()
    spy_cruds.reset_mock()
    spy_set.reset_mock()
    async with get_TestingSessionLocal()() as db:
        group_ids, account_types = await get_cached_permission_requirements(
            MyPaymentPermissions.access_payment,
            db,
            commons.SETTINGS,
            redis_client,
        )
    spy_get.assert_called_once_with(key)
    spy_cruds.assert_not_called()
    spy_set.assert_not_called()

    commons.SETTINGS.ENABLE_REDIS_CACHE = initial_ENABLE_REDIS_CACHE

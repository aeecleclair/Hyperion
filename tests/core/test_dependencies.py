import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth.schemas_auth import TokenData
from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import filter_user_token
from tests.commons import (
    create_groups_with_permissions,
    create_user_with_groups,
)

group1: models_groups.CoreGroup
group2: models_groups.CoreGroup

admin_user: TokenData
user_with_needed_account_type: TokenData
user_with_restricted_account_type: TokenData
user_external: TokenData
user_with_restricted_group: TokenData
user_with_needed_group: TokenData


def construct_token_data_from_user(user: models_users.CoreUser) -> TokenData:
    return TokenData(
        sub=user.id,
        group_ids=[str(group.id) for group in user.groups],
        account_type=user.account_type,
        school_id=user.school_id,
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
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
        [],
        "random group",
    )
    group2 = await create_groups_with_permissions(
        [],
        "random group2",
    )

    admin_user = construct_token_data_from_user(
        await create_user_with_groups(
            [GroupType.admin],
        ),
    )
    user_with_restricted_account_type = construct_token_data_from_user(
        await create_user_with_groups(
            [],
            AccountType.staff,
        ),
    )
    user_with_needed_account_type = construct_token_data_from_user(
        await create_user_with_groups([], AccountType.demo),
    )

    user_external = construct_token_data_from_user(
        await create_user_with_groups(
            [],
            AccountType.external,
        ),
    )

    user_with_restricted_group = construct_token_data_from_user(
        await create_user_with_groups(
            [group1.id],
        ),
    )

    user_with_needed_group = construct_token_data_from_user(
        await create_user_with_groups([group2.id]),
    )


def test_exclude_access_on_group(
    client: TestClient,
) -> None:
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

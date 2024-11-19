from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.core.schools.schools_type import SchoolType
from app.dependencies import is_user
from tests.commons import (
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
student_user: models_core.CoreUser
external_user: models_core.CoreUser
student_user_with_old_email: models_core.CoreUser
user_with_group: models_core.CoreUser

token_admin_user: str
token_student_user: str


UNIQUE_TOKEN = "my_unique_token"
FABRISTPP_EMAIL_1 = "fabristpp.eclair1@etu.ec-lyon.fr"
FABRISTPP_EMAIL_2 = "fabristpp.eclair3@ecl21.ec-lyon.fr"

student_user_email = "student@etu.ec-lyon.fr"
student_user_password = "password"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, student_user, student_user_with_old_email, external_user

    admin_user = await create_user_with_groups(
        [GroupType.admin],
        email=FABRISTPP_EMAIL_1,
    )
    student_user = await create_user_with_groups(
        [],
        email=student_user_email,
        password=student_user_password,
    )
    external_user = await create_user_with_groups([], AccountType.external)

    student_user_with_old_email = await create_user_with_groups(
        [],
        email=FABRISTPP_EMAIL_2,
    )

    global user_with_group
    user_with_group = await create_user_with_groups([GroupType.amap])

    global token_admin_user
    token_admin_user = create_api_access_token(admin_user)

    global token_student_user
    token_student_user = create_api_access_token(student_user)


def test_count_users(client: TestClient) -> None:
    response = client.get(
        "/users/count",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    assert response.json() >= 3


def test_search_users(client: TestClient) -> None:
    account_type = AccountType.student.value

    response = client.get(
        f"/users/?query=&accountTypes={account_type}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    account_type_users = set(user["id"] for user in response.json())

    response = client.get(
        f"/users/search?query=&includedAccountTypes={account_type}",
        headers={"Authorization": f"Bearer {token_student_user}"},
    )
    assert response.status_code == 200
    data_users = set(user["id"] for user in response.json())
    assert (
        data_users <= account_type_users
    )  # This endpoint is limited to 10 members, so we only need an inclusion between the two sets, in case there are more than 10 members in the group.

    response = client.get(
        f"/users/search?query=&excludedAccountTypes={account_type}",
        headers={"Authorization": f"Bearer {token_student_user}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(user["id"] not in account_type_users for user in data)


def test_get_account_types(client: TestClient) -> None:
    response = client.get(
        "/users/account-types",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == list(AccountType)


def test_restrict_access_on_group(client: TestClient) -> None:
    with pytest.raises(
        HTTPException,
        match="Unauthorized, user is a member of any of the groups ",
    ):
        is_user(
            excluded_groups=[GroupType.amap],
        )(user_with_group)


def test_read_current_user(client: TestClient) -> None:
    token = create_api_access_token(student_user)
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id


def test_read_user(client: TestClient) -> None:
    token = create_api_access_token(admin_user)
    response = client.get(
        f"/users/{student_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id
    # If the endpoint returns a CoreUserSimple, we could check that email was not returned
    # assert "email" not in data
    # Currently the endpoint return a CoreUser
    assert "email" in data


@pytest.mark.parametrize(
    ("email", "expected_code"),
    [
        ("fab@etu.ec-lyon.fr", 201),
        ("fab@ec-lyon.fr", 201),
        ("fab@centraliens-lyon.net", 201),
        ("fab@test.fr", 201),
        ("fab@ecl22.ec-lyon.fr", 201),
    ],
)
def test_create_user_by_user_with_email(
    email: str,
    expected_code: int,
    client: TestClient,
) -> None:
    response = client.post(
        "/users/create",
        json={
            "email": email,
            "school_id": SchoolType.centrale_lyon.value,
        },
    )
    assert response.status_code == expected_code


@pytest.mark.parametrize(
    ("email", "expected_code", "expected_account_type"),
    [
        ("fab1@etu.ec-lyon.fr", 201, AccountType.student),
        ("fab2@ec-lyon.fr", 201, AccountType.staff),
        ("fab3@centraliens-lyon.net", 201, AccountType.former_student),
        ("fab4@test.fr", 201, AccountType.external),
        ("fab5@ecl22.ec-lyon.fr", 201, AccountType.student),
    ],
)
def test_create_and_activate_user(
    email: str,
    expected_code: int,
    expected_account_type: AccountType,
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    # NOTE: we don't want to mock app.core.security.generate_token but
    # app.core.users.endpoints_users.security.generate_token which is the imported version of the function
    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )

    response = client.post(
        "/users/create",
        json={
            "email": "new_user@etu.ec-lyon.fr",
            "school_id": SchoolType.centrale_lyon.value,
        },
    )
    assert response.status_code == expected_code

    response = client.post(
        "/users/activate",
        json={
            "activation_token": UNIQUE_TOKEN,
            "password": "password",
            "firstname": "firstname",
            "name": email.split("@")[0],
            "nickname": "nickname",
            "floor": "X1",
        },
    )

    assert response.status_code == expected_code

    users = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    user = next(user for user in users.json() if user["name"] == email.split("@")[0])
    assert user is not None
    assert user["account_type"] == expected_account_type.value


@pytest.mark.parametrize(
    ("email", "expected_error"),
    [
        (
            "123456789",
            "Value error, Invalid phone number: (0) Missing or invalid default region.",
        ),
        ("+3300000000000", "Value error, Invalid phone number, number is not possible"),
        ("+33000000000", "Value error, Invalid phone number, number is not valid"),
    ],
)
def activate_user_with_invalid_phone_number(
    phone: str,
    expected_error: str,
    client: TestClient,
) -> None:
    response = client.post(
        "/users/activate",
        json={
            "activation_token": UNIQUE_TOKEN,
            "password": "password",
            "firstname": "firstname",
            "name": "name",
            "phone": phone,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == expected_error


def test_update_batch_create_users(client: TestClient) -> None:
    response = client.post(
        "/users/batch-creation",
        json=[
            {"email": "1@1.fr", "school_id": SchoolType.centrale_lyon.value},
            {"email": "2@1.fr", "school_id": SchoolType.centrale_lyon.value},
            {"email": "3@b.fr", "school_id": SchoolType.centrale_lyon.value},
        ],
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 201


def test_can_not_make_admin_when_there_are_multiple_users(client: TestClient) -> None:
    response = client.post(
        "/users/make-admin",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 403


def test_recover_and_reset_password(mocker: MockerFixture, client: TestClient) -> None:
    # NOTE: we don't want to mock app.core.security.generate_token but
    # app.core.users.endpoints_users.security.generate_token which is the imported version of the function
    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )

    response = client.post(
        "/users/recover",
        json={"email": FABRISTPP_EMAIL_1},
    )

    assert response.status_code == 201

    response = client.post(
        "/users/reset-password",
        json={"reset_token": UNIQUE_TOKEN, "new_password": "new_password"},
    )

    assert response.status_code == 201


def test_recover_with_non_existing_account(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    mocked_hyperion_security_logger = mocker.patch(
        "app.core.users.endpoints_users.hyperion_security_logger.info",
    )

    response = client.post(
        "/users/recover",
        json={"email": "non-existing@myecl.fr"},
    )

    assert response.status_code == 201

    mocked_hyperion_security_logger.assert_called_once_with(
        "Reset password failed for non-existing@myecl.fr, user does not exist",
    )


def test_update_user(client: TestClient) -> None:
    # A non admin user should not be allowed to use this endpoint
    token = create_api_access_token(student_user)
    response = client.patch(
        f"/users/{student_user.id}",
        json={"nickname": "NewNickName2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    # An admin user is allowed to update users
    token = create_api_access_token(admin_user)
    response = client.patch(
        f"/users/{student_user.id}",
        json={"nickname": "NewNickName"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


async def test_migrate_mail(mocker: MockerFixture, client: TestClient) -> None:
    # NOTE: we don't want to mock app.core.security.generate_token but
    # app.core.users.endpoints_users.security.generate_token which is the imported version of the function
    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )

    token = create_api_access_token(student_user_with_old_email)

    # Start the migration process
    response = client.post(
        "/users/migrate-mail",
        json={"new_email": "fabristpp.eclair@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Try invalid confirmation code
    response = client.get(
        "/users/migrate-mail-confirm",
        params={"token": "an other token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404

    # Confirm the migration
    response = client.get(
        "/users/migrate-mail-confirm",
        params={"token": UNIQUE_TOKEN},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_change_password(client: TestClient) -> None:
    response = client.post(
        "/users/change-password",
        json={
            "email": student_user_email,
            "old_password": student_user_password,
            "new_password": "the_new_password",
        },
        headers={"Authorization": f"Bearer {token_student_user}"},
    )
    assert response.status_code == 201


def test_read_users(client: TestClient) -> None:
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200


def test_update_current_user(client: TestClient) -> None:
    token = create_api_access_token(admin_user)
    response = client.patch(
        "/users/me",
        json={"nickname": "NewNickName2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_create_current_user_profile_picture(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    with Path("assets/images/default_profile_picture.png").open("rb") as image:
        response = client.post(
            "/users/me/profile-picture",
            files={"image": ("profile picture.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_read_own_profile_picture(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        "/users/me/profile-picture",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_read_user_profile_picture(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        f"/users/{admin_user.id}/profile-picture",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

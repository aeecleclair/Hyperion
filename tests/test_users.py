from pathlib import Path

import pytest
import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import (
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)

admin_user: models_core.CoreUser
student_user: models_core.CoreUser

student_user_with_old_email: models_core.CoreUser

token_admin_user: str
token_student_user: str


UNIQUE_TOKEN = "my_unique_token"
FABRISTPP_EMAIL_1 = "fabristpp.eclair1@etu.ec-lyon.fr"
FABRISTPP_EMAIL_2 = "fabristpp.eclair3@ecl21.ec-lyon.fr"

student_user_email = "student@etu.ec-lyon.fr"
student_user_password = "password"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global admin_user, student_user, student_user_with_old_email

    admin_user = await create_user_with_groups(
        [GroupType.admin],
        email=FABRISTPP_EMAIL_1,
    )
    student_user = await create_user_with_groups(
        [GroupType.student],
        email=student_user_email,
        password=student_user_password,
    )

    student_user_with_old_email = await create_user_with_groups(
        [GroupType.student],
        email=FABRISTPP_EMAIL_2,
    )

    global token_admin_user
    token_admin_user = create_api_access_token(admin_user)

    global token_student_user
    token_student_user = create_api_access_token(student_user)


def test_count_users():
    response = client.get(
        "/users/count",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    assert response.json() >= 3


def test_search_users():
    group = GroupType.student.value

    response = client.get(
        f"/groups/{group}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    group_users = set(member["id"] for member in response.json()["members"])

    response = client.get(
        f"/users/search?query=&includedGroups={group}",
        headers={"Authorization": f"Bearer {token_student_user}"},
    )
    assert response.status_code == 200
    data_users = set(user["id"] for user in response.json())
    assert (
        data_users <= group_users
    )  # This endpoint is limited to 10 members, so we only need an inclusion between the two sets, in case there are more than 10 members in the group.

    response = client.get(
        f"/users/search?query=&excludedGroups={group}",
        headers={"Authorization": f"Bearer {token_student_user}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(user["id"] not in group_users for user in data)


def test_read_current_user():
    token = create_api_access_token(student_user)
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id


def test_read_user():
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
        ("fab@test.fr", 400),
        ("fab@ecl22.ec-lyon.fr", 400),
    ],
)
def test_create_user_by_user_with_email(email, expected_code):
    response = client.post(
        "/users/create",
        json={
            "email": email,
        },
    )
    assert response.status_code == expected_code


def test_create_and_activate_user(mocker):
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
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/users/activate",
        json={
            "activation_token": UNIQUE_TOKEN,
            "password": "password",
            "firstname": "firstname",
            "name": "name",
            "nickname": "nickname",
            "floor": "X1",
        },
    )

    assert response.status_code == 201


def test_update_batch_create_users():
    student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    response = client.post(
        "/users/batch-creation",
        json=[
            {"email": "1@1.fr", "account_type": student},
            {"email": "2@1.fr", "account_type": student},
            {"email": "3@b.fr", "account_type": student},
        ],
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 201


def test_can_not_make_admin_when_there_are_multiple_users():
    response = client.post(
        "/users/make-admin",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 403


def test_recover_and_reset_password(mocker):
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


def test_update_user():
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


async def test_invalid_migrate_mail():
    student_user_with_old_email_token = create_api_access_token(
        student_user_with_old_email,
    )
    other_student_user_token = create_api_access_token(student_user)

    # Invalid old mail format
    response = client.post(
        "/users/migrate-mail",
        json={"new_email": "fabristpp.eclair@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {other_student_user_token}"},
    )
    assert response.status_code == 400

    # Invalid new mail format
    response = client.post(
        "/users/migrate-mail",
        json={"new_email": "fabristpp.eclair@test.fr"},
        headers={"Authorization": f"Bearer {student_user_with_old_email_token}"},
    )
    assert response.status_code == 400


async def test_migrate_mail(mocker):
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


def test_change_password():
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


def test_read_users():
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200


def test_update_current_user():
    token = create_api_access_token(admin_user)
    response = client.patch(
        "/users/me",
        json={"nickname": "NewNickName2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_create_current_user_profile_picture():
    token = create_api_access_token(student_user)

    with Path("assets/images/default_profile_picture.png").open("rb") as image:
        response = client.post(
            "/users/me/profile-picture",
            files={"image": ("profile picture.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_read_own_profile_picture():
    token = create_api_access_token(student_user)

    response = client.get(
        "/users/me/profile-picture",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_read_user_profile_picture():
    token = create_api_access_token(student_user)

    response = client.get(
        f"/users/{admin_user.id}/profile-picture",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

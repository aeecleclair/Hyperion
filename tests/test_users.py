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

admin_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None

student_user_with_old_email: models_core.CoreUser | None = None

UNIQUE_TOKEN = "my_unique_token"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global admin_user, student_user, student_user_with_old_email

    admin_user = await create_user_with_groups([GroupType.admin])
    student_user = await create_user_with_groups([GroupType.student])

    student_user_with_old_email = await create_user_with_groups(
        [GroupType.student],
        email="fabristpp.eclair@ecl21.ec-lyon.fr",
    )


def test_read_users():
    token = create_api_access_token(admin_user)
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


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


def test_update_current_user():
    token = create_api_access_token(admin_user)
    response = client.patch(
        "/users/me",
        json={"nickname": "NewNickName2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


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


def test_create_current_user_profile_picture():
    token = create_api_access_token(student_user)

    with open("assets/images/default_profile_picture.png", "rb") as image:
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


def test_search_users():
    group = GroupType.student.value

    token = create_api_access_token(admin_user)
    response = client.get(
        f"/groups/{group}",
        headers={"Authorization": f"Bearer {token}"},
    )
    group_users = set(member["id"] for member in response.json()["members"])

    token = create_api_access_token(student_user)

    response = client.get(
        f"/users/search?query=&includedGroups={group}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data_users = set(user["id"] for user in response.json())
    assert (
        data_users <= group_users
    )  # This endpoint is limited to 10 members, so we only need an inclusion between the two sets, in case there are more than 10 members in the group.

    response = client.get(
        f"/users/search?query=&excludedGroups={group}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(user["id"] not in group_users for user in data)


async def test_invalid_migrate_mail():
    student_user_with_old_email_token = create_api_access_token(
        student_user_with_old_email
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

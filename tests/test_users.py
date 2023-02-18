from app.main import app
from app.models import models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global admin_user, student_user

    async with TestingSessionLocal() as db:
        admin_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        await db.commit()


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
    assert data_users == group_users

    response = client.get(
        f"/users/search?query=&excludedGroups={group}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all([user["id"] not in group_users for user in data])

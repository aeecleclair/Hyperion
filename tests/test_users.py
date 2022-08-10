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


@app.on_event("startup")  # create the datas needed in the tests
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
    token = create_api_access_token(student_user)
    response = client.get(
        f"/users/{student_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id
    # The endpoint should not return to much information
    assert "email" not in data


def test_update_current_user():

    token = create_api_access_token(admin_user)
    response = client.patch(
        "/users/me",
        json={"name": "NewName2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    data = response.json()
    # We want to make sure the name was changed
    assert data["name"] == "NewName2"


def test_update_user():

    # A non admin user should not be allowed to use this endpoint
    token = create_api_access_token(student_user)
    response = client.patch(
        f"/users/{student_user.id}",
        json={"name": "NewName"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    # An admin user is allowed to update users
    token = create_api_access_token(admin_user)
    response = client.patch(
        f"/users/{student_user.id}",
        json={"name": "NewName"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # We want to make sure the name was changed
    assert data["name"] == "NewName"


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

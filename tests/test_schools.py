import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.core.schools.schools_type import SchoolType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
ens_user: models_core.CoreUser
new_school_user: models_core.CoreUser

UNIQUE_TOKEN = "my_unique_token"

id_test_ens = "4d133de7-24c4-4dbc-be73-4705a2ddd315"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, ens_user, new_school_user

    ens = models_core.CoreSchool(
        id=id_test_ens,
        name="ENS",
        email_regex=r"^.*@ens.fr$",
    )
    await add_object_to_db(ens)

    admin_user = await create_user_with_groups([GroupType.admin])

    ens_user = await create_user_with_groups(
        [],
        school_id=id_test_ens,
        email="test@ens.fr",
        account_type=AccountType.other_school_student,
    )

    new_school_user = await create_user_with_groups(
        [],
        school_id=SchoolType.no_school,
        email="test@school.fr",
        account_type=AccountType.external,
    )


def test_read_schools(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.get(
        "/schools/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_read_school(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.get(
        f"/schools/{id_test_ens}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ENS"


def test_create_school(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    school = client.post(
        "/schools/",
        json={
            "name": "school",
            "email_regex": r"^.*@school\.fr$",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert school.status_code == 201

    response = client.get(
        f"/users/{new_school_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["school_id"] == school.json()["id"]


def test_update_school(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.patch(
        f"/schools/{id_test_ens}",
        json={"name": "school ENS", "email_regex": r"^.*@.*ens.fr$"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/schools/{id_test_ens}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["name"] == "school ENS"


def test_create_user_corresponding_to_school(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    token = create_api_access_token(admin_user)

    response = client.post(
        "/schools/",
        json={
            "name": "ENS Lyon",
            "email_regex": r"^[\w\-.]*@ens-lyon\.fr$",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    school_id = response.json()["id"]

    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )

    response = client.post(
        "/users/create",
        json={
            "email": "new_user@ens-lyon.fr",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/users/activate",
        json={
            "activation_token": UNIQUE_TOKEN,
            "password": "password",
            "firstname": "new_user_firstname",
            "name": "new_user_name",
        },
    )

    assert response.status_code == 201

    users = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    user = next(
        user
        for user in users.json()
        if user["firstname"] == "new_user_firstname" and user["name"] == "new_user_name"
    )

    user_detail = client.get(
        f"/users/{user['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert user_detail.json()["school_id"] == school_id


def test_delete_school(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.delete(
        f"/schools/{id_test_ens}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/schools/{id_test_ens}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "School not found"}

    response = client.get(
        f"/users/{ens_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["school_id"] == SchoolType.no_school

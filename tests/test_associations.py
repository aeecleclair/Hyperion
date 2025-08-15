import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.associations import models_associations
from app.core.groups.groups_type import GroupType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

user_token: str
admin_user_token: str
eclair_user_token: str

id_association = uuid.UUID("8aab79e7-1e15-456d-b6e2-11e4e9f77e4f")


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global user_token, admin_user_token, eclair_user_token

    eclair_association = models_associations.CoreAssociation(
        id=id_association,
        name="test_association_eclair",
        group_id=GroupType.eclair,
    )
    await add_object_to_db(eclair_association)

    admin_user = await create_user_with_groups([GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)

    eclair_user = await create_user_with_groups([GroupType.eclair])
    eclair_user_token = create_api_access_token(eclair_user)

    user = await create_user_with_groups([])
    user_token = create_api_access_token(user)


def test_get_associations(client: TestClient) -> None:
    response = client.get(
        "/associations/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(id_association)
    assert data[0]["name"] == "test_association_eclair"


def test_get_associations_me_without_associations(client: TestClient) -> None:
    response = client.get(
        "/associations/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_get_associations_me_with_associations(client: TestClient) -> None:
    response = client.get(
        "/associations/me",
        headers={"Authorization": f"Bearer {eclair_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(id_association)
    assert data[0]["name"] == "test_association_eclair"


def test_create_association(client: TestClient) -> None:
    response = client.post(
        "/associations/",
        json={
            "name": "TestAsso",
            "group_id": GroupType.eclair.value,
        },
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 201


def test_update_association(client: TestClient) -> None:
    response = client.patch(
        f"/associations/{id_association}",
        json={
            "name": "Group ECLAIR",
        },
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 204


def test_create_and_read_logo(client: TestClient) -> None:
    with Path("assets/images/default_profile_picture.png").open("rb") as image:
        response = client.post(
            f"/associations/{id_association}/logo",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )
    assert response.status_code == 204

    response = client.get(
        f"/associations/{id_association}/logo",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200

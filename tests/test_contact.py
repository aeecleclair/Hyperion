import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.modules.misc import models_misc
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

token_simple: str
token_eclair: str
contact: models_misc.Contacts


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    user_simple = await create_user_with_groups(
        [],
    )

    global token_simple
    token_simple = create_api_access_token(user_simple)

    user_eclair = await create_user_with_groups([GroupType.eclair])

    global token_eclair
    token_eclair = create_api_access_token(user_eclair)

    global contact
    contact = models_misc.Contacts(
        id=uuid.uuid4(),
        creation=datetime.now(UTC),
        name="John Doe",
        phone="123456789",
        email="johndoe@example.com",
        location="Lyon",
    )
    await add_object_to_db(contact)


def test_get_contacts(client: TestClient) -> None:
    response = client.get(
        "/contact/contacts",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_contact(client: TestClient) -> None:
    response = client.post(
        "/contact/contacts",
        json={
            "name": "Jane Doe",
            "phone": "987654321",
            "email": "janedoe@example.com",
            "location": "Lyon",
        },
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 201


def test_create_contact_with_no_body(client: TestClient) -> None:
    response = client.post(
        "/contact/contacts",
        json={},
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 422


def test_edit_contact(client: TestClient) -> None:
    response = client.patch(
        f"/contact/contacts/{contact.id}",
        json={"name": "John Smith"},
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 204


def test_edit_contact_with_no_body(client: TestClient) -> None:
    response = client.patch(
        f"/contact/contacts/{contact.id}",
        json={},
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 204


def test_edit_for_non_existing_contact(client: TestClient) -> None:
    false_id = "098cdfb7-609a-493f-8d5a-47bbdba213da"
    response = client.patch(
        f"/contact/contacts/{false_id}",
        json={"name": "Nonexistent Contact"},
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 404


def test_delete_contact(client: TestClient) -> None:
    response = client.delete(
        f"/contact/contacts/{contact.id}",
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 204


def test_delete_for_non_existing_contact(client: TestClient) -> None:
    false_id = "cfba17a6-58b8-4595-afb9-3c9e4e169a14"
    response = client.delete(
        f"/contact/contacts/{false_id}",
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 404

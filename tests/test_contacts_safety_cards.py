import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from tests.commons import create_api_access_token, create_user_with_groups

token_simple: str
token_eclair: str


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


def test_get_contacts(client: TestClient) -> None:
    response = client.get(
        "/contacts_safety_cards/contacts",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_set_contacts(client: TestClient) -> None:
    response = client.put(
        "/contacts_safety_cards/contacts/",
        json=[
            {
                "name": "John Doe",
                "phone": "123456789",
                "email": "johndoe@example.com",
                "location": "Lyon",
            },
            {
                "name": "John Doe bis",
                "phone": "323456789",
                "email": "johndoebis@example.com",
                "location": "Ecully",
            },
        ],
        headers={"Authorization": f"Bearer {token_eclair}"},
    )
    assert response.status_code == 201

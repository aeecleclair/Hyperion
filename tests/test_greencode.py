import uuid

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.modules.greencode import models_greencode
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)

item: models_greencode.GreenCodeItem | None = None

token_simple: str = ""
token_greencode: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global user_simple
    user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(user_simple)

    global user_with_membership
    user_with_membership = await create_user_with_groups(
        [
            GroupType.student,
        ],
    )

    global token_with_membership
    token_with_membership = create_api_access_token(user_with_membership)

    global user_greencode
    user_greencode = await create_user_with_groups(
        [GroupType.student, GroupType.greencode],
    )

    global token_greencode
    token_greencode = create_api_access_token(user_greencode)

    global item
    item = models_greencode.GreenCodeItem(
        id=str(uuid.uuid4()),
        qr_code_content="QRCodeContent",
        title="Item",
        content="Example of item",
    )
    await add_object_to_db(item)

    global item_to_delete
    item_to_delete = models_greencode.GreenCodeItem(
        id=str(uuid.uuid4()),
        qr_code_content="Another QRCodeContent",
        title="Item to delete",
        content="I will be deleted soon!",
    )
    await add_object_to_db(item_to_delete)

    membership = models_greencode.GreenCodeMembership(
        id=str(uuid.uuid4()),
        user_id=user_with_membership.id,
        item_id=item.id,
    )

    await add_object_to_db(membership)


def test_get_items_for_user_simpe():
    response = client.get(
        "/greencode/items",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_items_for_user_greencode():
    response = client.get(
        "/greencode/items",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == item.id


def test_get_user_items():
    response = client.get(
        "/greencode/items/me",
        headers={"Authorization": f"Bearer {token_with_membership}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == item.id


def test_get_item_by_qr_code():
    response = client.get(
        f"/greencode/{item.qr_code_content}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == item.id


def test_create_item():
    response = client.post(
        "/greencode/item",
        json={
            "qr_code_content": "QRCodeContent 2nd",
            "title": "Item",
            "content": "Example of item",
        },
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 201
    assert response.json()["id"] is not None


def test_create_item_simple():
    response = client.post(
        "/greencode/item",
        json={
            "qr_code_content": "QRCodeContent 3rd",
            "title": "Item",
            "content": "Example of item",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_item_simple():
    response = client.delete(
        f"/greencode/item/{item_to_delete.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_item():
    response = client.delete(
        f"/greencode/item/{item_to_delete.id}",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 204


def test_update_item_simple():
    response = client.patch(
        f"/greencode/item/{item.id}",
        json={"title": "Item Updated"},
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_item():
    response = client.patch(
        f"/greencode/item/{item.id}",
        json={"title": "Item Updated"},
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 204


def test_get_completions_simple():
    response = client.get(
        "/greencode/completion/all",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_completions():
    response = client.get(
        "/greencode/completion/all",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_completion_simple():
    response = client.get(
        f"/greencode/completion/{user_with_membership.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_completion_greencode():
    response = client.get(
        f"/greencode/completion/{user_with_membership.id}",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 200
    assert response.json()["discovered_count"] == 1


def test_get_user_completion():
    response = client.get(
        "/greencode/completion/me",
        headers={"Authorization": f"Bearer {token_with_membership}"},
    )
    assert response.status_code == 200
    assert response.json()["discovered_count"] == 1


def test_create_membership_simple():
    response = client.post(
        f"/greencode/item/{item.id}/{user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_create_membership():
    response = client.post(
        f"/greencode/item/{item.id}/{user_simple.id}",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 204


def test_delete_membership_simple():
    response = client.delete(
        f"/greencode/item/{item.id}/{user_simple.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_delete_membership():
    response = client.delete(
        f"/greencode/item/{item.id}/{user_simple.id}",
        headers={"Authorization": f"Bearer {token_greencode}"},
    )
    assert response.status_code == 204


def test_create_current_user_membership():
    response = client.post(
        f"/greencode/item/{item.id}/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204


def test_delete_current_user_membership():
    response = client.delete(
        f"/greencode/item/{item.id}/me",
        headers={"Authorization": f"Bearer {token_with_membership}"},
    )
    assert response.status_code == 204

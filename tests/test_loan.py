import datetime
import uuid
from datetime import timedelta

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.loan import models_loan
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
loan_user_loaner: models_core.CoreUser
loan_user_simple: models_core.CoreUser
loaner: models_loan.Loaner
loaner_to_delete: models_loan.Loaner
loan: models_loan.Loan
item: models_loan.Item
item_to_delete: models_loan.Item
token_loaner: str
token_simple: str
token_admin: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user
    global loan_user_loaner
    global loaner
    global loan_user_simple
    global loaner_to_delete
    global loan
    global item
    global item_to_delete
    admin_user = await create_user_with_groups([GroupType.admin])

    loan_user_loaner = await create_user_with_groups([GroupType.CAA])
    loaner = models_loan.Loaner(
        id=str(uuid.uuid4()),
        name="CAA",
        group_manager_id="6c6d7e88-fdb8-4e42-b2b5-3d3cfd12e7d6",
    )
    await add_object_to_db(loaner)

    loan_user_simple = await create_user_with_groups([GroupType.amap])

    loaner_to_delete = models_loan.Loaner(
        id=str(uuid.uuid4()),
        name="cinema",
        group_manager_id="ce5f36e6-5377-489f-9696-de70e2477300",
    )
    await add_object_to_db(loaner_to_delete)

    item = models_loan.Item(
        id=str(uuid.uuid4()),
        name="Test Item",
        loaner_id=loaner.id,
        suggested_lending_duration=timedelta(
            days=50,
        ).seconds,
        suggested_caution=10,
        total_quantity=8,
        loaner=loaner,
    )
    await add_object_to_db(item)

    item_to_delete = models_loan.Item(
        id=str(uuid.uuid4()),
        name="Test Item To Delete",
        loaner_id=loaner.id,
        suggested_lending_duration=timedelta(
            days=50,
        ).seconds,
        suggested_caution=10,
        total_quantity=5,
        loaner=loaner,
    )
    await add_object_to_db(item_to_delete)
    loan = models_loan.Loan(
        id=str(uuid.uuid4()),
        borrower_id=loan_user_simple.id,
        loaner_id=loaner.id,
        start=datetime.date(year=2023, month=3, day=29),
        end=datetime.date(year=2023, month=4, day=26),
        caution="Carte etudiante",
        returned=False,
        items=[item],
    )
    await add_object_to_db(loan)

    global token_admin
    token_admin = create_api_access_token(admin_user)

    global token_loaner
    token_loaner = create_api_access_token(loan_user_loaner)

    global token_simple
    token_simple = create_api_access_token(loan_user_simple)


def test_get_loaners(client: TestClient) -> None:
    response = client.get(
        "/loans/loaners/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_create_loaners(client: TestClient) -> None:
    response = client.post(
        "/loans/loaners/",
        json={
            "name": "BDE",
            "group_manager_id": "ce5f36e6-5377-489f-9696-de70e2477300",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_update_loaners(client: TestClient) -> None:
    response = client.patch(
        f"/loans/loaners/{loaner_to_delete.id}",
        json={
            "name": "AE",
            "group_manager_id": "45649735-866a-49df-b04b-a13c74fd5886",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_loaners(client: TestClient) -> None:
    response = client.delete(
        f"/loans/loaners/{loaner_to_delete.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_get_loans_by_loaner(client: TestClient) -> None:
    response = client.get(
        f"/loans/loaners/{loaner.id}/loans",
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 200


def test_get_items_for_loaner(client: TestClient) -> None:
    response = client.get(
        f"/loans/loaners/{loaner.id}/items",
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 200


def test_create_items_for_loaner(client: TestClient) -> None:
    response = client.post(
        f"/loans/loaners/{loaner.id}/items",
        json={
            "name": "TestItem",
            "suggested_caution": 100,
            "total_quantity": 4,
            "suggested_lending_duration": timedelta(days=10).seconds,
        },
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 201


def test_update_items_for_loaner(client: TestClient) -> None:
    response = client.patch(
        f"/loans/loaners/{loaner.id}/items/{item.id}",
        json={
            "name": "TestItem",
            "suggested_caution": 100,
            "total_quantity": 7,
            "suggested_lending_duration": timedelta(days=10).seconds,
        },
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204


def test_delete_loaner_item(client: TestClient) -> None:
    response = client.delete(
        f"/loans/loaners/{loaner.id}/items/{item_to_delete.id}",
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204


def test_get_current_user_loans(client: TestClient) -> None:
    response = client.get(
        "/loans/users/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_current_user_loaners(client: TestClient) -> None:
    response = client.get(
        "/loans/users/me/loaners",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_loan(client: TestClient) -> None:
    response = client.post(
        "/loans/",
        json={
            "borrower_id": loan_user_simple.id,
            "loaner_id": loaner.id,
            "start": "2022-10-23",
            "end": "2022-10-23",
            "notes": "Je pense que cela va fonctionner à merveille :)",
            "caution": "20€",
            "items_borrowed": [
                {
                    "item_id": item.id,
                    "quantity": 2,
                },
            ],
        },
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 201


def test_update_loan(client: TestClient) -> None:
    response = client.patch(
        f"/loans/{loan.id}",
        json={
            "borrower_id": loan_user_simple.id,
            "start": "2022-10-23",
            "end": "2022-10-23",
            "notes": "Je pense que cela va fonctionner à merveille :)",
            "caution": "20€",
            "returned": True,
            "items_borrowed": [
                {
                    "item_id": item.id,
                    "quantity": 2,
                },
            ],
        },
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204


def test_return_loan(client: TestClient) -> None:
    response = client.post(
        f"/loans/{loan.id}/return",
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204


def test_extend_loan(client: TestClient) -> None:
    response = client.post(
        f"/loans/{loan.id}/extend",
        json={
            "end": "2024-05-25",
        },
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204


def test_delete_loan(client: TestClient) -> None:
    response = client.delete(
        f"/loans/{loan.id}",
        headers={"Authorization": f"Bearer {token_loaner}"},
    )
    assert response.status_code == 204

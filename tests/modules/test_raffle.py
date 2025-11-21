import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.raffle import models_raffle
from app.modules.raffle.types_raffle import RaffleStatusType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

BDE_user: models_users.CoreUser
admin_user: models_users.CoreUser
student_user: models_users.CoreUser
raffle: models_raffle.Raffle
raffle_to_draw: models_raffle.Raffle
raffle_to_delete: models_raffle.Raffle
packticket: models_raffle.PackTicket
packticket_to_draw: models_raffle.PackTicket
packticket_to_delete: models_raffle.PackTicket
prize: models_raffle.Prize
prize_to_draw: models_raffle.Prize
ticket: models_raffle.Ticket
ticket_to_draw: models_raffle.Ticket
cash: models_raffle.Cash


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global \
        admin_user, \
        BDE_user, \
        student_user, \
        raffle, \
        raffle_to_draw, \
        packticket, \
        packticket_to_draw, \
        ticket, \
        ticket_to_draw, \
        prize, \
        prize_to_draw, \
        cash, \
        raffle_to_delete, \
        packticket_to_delete

    BDE_user = await create_user_with_groups([GroupType.BDE])
    student_user = await create_user_with_groups(
        [],
    )
    admin_user = await create_user_with_groups([GroupType.admin])

    raffle_to_delete = models_raffle.Raffle(
        id=str(uuid.uuid4()),
        name="Antoine's raffle",
        status=RaffleStatusType.creation,
        group_id=GroupType.BDE,
        description=None,
    )
    await add_object_to_db(raffle_to_delete)
    raffle = models_raffle.Raffle(
        id=str(uuid.uuid4()),
        name="The best raffle",
        status=RaffleStatusType.creation,
        group_id=GroupType.BDE,
        description="Description of the raffle",
    )
    await add_object_to_db(raffle)

    raffle_to_draw = models_raffle.Raffle(
        id=str(uuid.uuid4()),
        name="The best raffle to draw",
        status=RaffleStatusType.lock,
        group_id=GroupType.BDE,
        description="Description of the raffle",
    )
    await add_object_to_db(raffle_to_draw)

    packticket = models_raffle.PackTicket(
        id=str(uuid.uuid4()),
        price=1.0,
        pack_size=1,
        raffle_id=raffle.id,
    )
    await add_object_to_db(packticket)

    packticket_to_draw = models_raffle.PackTicket(
        id=str(uuid.uuid4()),
        price=1.0,
        pack_size=1,
        raffle_id=raffle_to_draw.id,
    )
    await add_object_to_db(packticket_to_draw)

    packticket_to_delete = models_raffle.PackTicket(
        id=str(uuid.uuid4()),
        price=1.0,
        pack_size=1,
        raffle_id=raffle_to_delete.id,
    )
    await add_object_to_db(packticket_to_delete)

    ticket = models_raffle.Ticket(
        id=str(uuid.uuid4()),
        pack_id=packticket.id,
        user_id=student_user.id,
    )
    await add_object_to_db(ticket)

    ticket_to_draw = models_raffle.Ticket(
        id=str(uuid.uuid4()),
        pack_id=packticket_to_draw.id,
        user_id=student_user.id,
    )
    await add_object_to_db(ticket_to_draw)

    prize = models_raffle.Prize(
        id=str(uuid.uuid4()),
        raffle_id=raffle.id,
        description="Description of the prize",
        name="Name of the prize",
        quantity=1,
    )
    await add_object_to_db(prize)

    prize_to_draw = models_raffle.Prize(
        id=str(uuid.uuid4()),
        raffle_id=raffle_to_draw.id,
        description="Description of the prize",
        name="Name of the prize",
        quantity=1,
    )
    await add_object_to_db(prize_to_draw)

    cash = models_raffle.Cash(user_id=student_user.id, balance=66)
    await add_object_to_db(cash)


def test_get_raffles(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        "/tombola/raffles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_raffle(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.post(
        "/tombola/raffles",
        json={
            "name": "test",
            "group_id": GroupType.BDE,
            "description": "Raffle's description",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_raffle(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.patch(
        f"/tombola/raffles/{raffle_to_delete.id}",
        json={
            "name": "testupdate",
            "description": "Raffle's description",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/tombola/raffles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    json = response.json()
    [modified_raffle] = [entry for entry in json if entry["id"] == raffle_to_delete.id]
    assert modified_raffle["name"] == "testupdate"


def test_create_raffle_logo(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    with Path("assets/images/default_campaigns_logo.png").open("rb") as image:
        response = client.post(
            f"/tombola/raffles/{raffle.id}/logo",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_read_raffle_logo(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.get(
        f"/tombola/raffles/{raffle.id}/logo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_create_prize_picture(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    with Path("assets/images/default_campaigns_logo.png").open("rb") as image:
        response = client.post(
            f"/tombola/prizes/{prize.id}/picture",
            files={"image": ("logo.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201


def test_read_prize_picture(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.get(
        f"/tombola/prizes/{prize.id}/picture",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_open_raffle(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.patch(
        f"/tombola/raffles/{raffle_to_delete.id}/open",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/tombola/raffles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    json = response.json()
    [modified_raffle] = [entry for entry in json if entry["id"] == raffle_to_delete.id]
    assert modified_raffle["status"] == RaffleStatusType.open


def test_lock_raffle(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.patch(
        f"/tombola/raffles/{raffle_to_delete.id}/lock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/tombola/raffles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    json = response.json()
    [modified_raffle] = [entry for entry in json if entry["id"] == raffle_to_delete.id]
    assert modified_raffle["status"] == RaffleStatusType.lock


def test_get_raffle_stats(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/raffles/{raffle.id}/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["amount_raised"] == 1.0


# # tickets
def test_get_tickets(client: TestClient) -> None:
    token = create_api_access_token(admin_user)

    response = client.get(
        "/tombola/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_tickets_by_raffle_id(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.get(
        f"/tombola/raffles/{raffle.id}/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_tickets_by_user_id(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/users/{student_user.id}/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_buy_tickets(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.post(
        f"/tombola/tickets/buy/{packticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201


# def test_edit_tickets():
#     token = create_api_access_token(BDE_user)

#     response = client.patch(
#         f"/tombola/tickets/{ticket.id}",
#         json={
#             "user_id": BDE_user.id,
#             "raffle_id": raffle.id,
#             "pack_id": packticket.id,
#             "winning_prize": None,
#             "nb_tickets": 10,
#         },
#         headers={"Authorization": f"Bearer {token}"},
#     )
#     assert response.status_code == 204


# def test_delete_tickets():
#     token = create_api_access_token(BDE_user)

#     response = client.delete(
#         f"/tombola/tickets/{ticket.id}",
#         headers={"Authorization": f"Bearer {token}"},
#     )
#     assert response.status_code == 204


# # pack_tickets
def test_get_packtickets(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.get(
        "/tombola/pack_tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_packtickets_by_raffle_id(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.get(
        f"/tombola/raffles/{raffle.id}/pack_tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_packtickets(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.post(
        "/tombola/pack_tickets",
        json={
            "raffle_id": raffle.id,
            "price": 1.23,
            "pack_size": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_packtickets(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.patch(
        f"/tombola/pack_tickets/{packticket.id}",
        json={
            "raffle_id": raffle.id,
            "price": 10.0,
            "pack_size": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_packtickets(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.delete(
        f"/tombola/pack_tickets/{packticket_to_delete.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


# # prizes
def test_get_prizes(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        "/tombola/prizes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_prizes_by_raffle_id(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/raffles/{raffle.id}/prizes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() != []


def test_create_prizes(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.post(
        "/tombola/prizes",
        json={
            "raffle_id": raffle.id,
            "description": "Prizes description",
            "name": "Prizes name",
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_prizes(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.patch(
        f"/tombola/prizes/{prize.id}",
        json={
            "raffle_id": raffle.id,
            "description": "Prizes description updated",
            "name": "Prizes name",
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_draw_prizes(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.post(
        f"/tombola/prizes/{prize_to_draw.id}/draw",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tickets = response.json()
    assert tickets[0]["prize"] is not None


def test_delete_prizes(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.delete(
        f"/tombola/prizes/{prize.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_raffle(client: TestClient) -> None:
    token = create_api_access_token(BDE_user)

    response = client.delete(
        f"/tombola/raffles/{raffle_to_delete.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

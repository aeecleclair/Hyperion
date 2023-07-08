import uuid

import pytest_asyncio

from app.models import models_core, models_raffle
from app.utils.types.groups_type import GroupType
from app.utils.types.raffle_types import RaffleStatusType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    change_redis_client_status,
    client,
    create_api_access_token,
    create_user_with_groups,
)

soli_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None
raffle: models_raffle.Raffle | None = None
raffle_to_delete: models_raffle.Raffle | None = None
typeticket: models_raffle.TypeTicket | None = None
typeticket_to_delete: models_raffle.TypeTicket | None = None
lot: models_raffle.Lots | None = None
ticket: models_raffle.Tickets | None = None
cash: models_raffle.Cash | None = None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_objects():
    global soli_user, student_user, raffle, typeticket, ticket, lot, cash, raffle_to_delete, typeticket_to_delete

    soli_user = await create_user_with_groups([GroupType.soli])
    student_user = await create_user_with_groups([GroupType.student])

    raffle_to_delete = models_raffle.Raffle(
        id=str(uuid.uuid4()),
        name="Antoine's raffle",
        status=RaffleStatusType.creation,
        group_id=GroupType.soli,
    )
    await add_object_to_db(raffle_to_delete)
    raffle = models_raffle.Raffle(
        id=str(uuid.uuid4()),
        name="The best raffle",
        status=RaffleStatusType.locked,
        group_id=GroupType.soli,
        description="Description of the raffle",
    )
    await add_object_to_db(raffle)

    typeticket = models_raffle.TypeTicket(
        id=str(uuid.uuid4()), price=1.0, pack_size=1, raffle_id=raffle.id
    )
    await add_object_to_db(typeticket)
    typeticket_to_delete = models_raffle.TypeTicket(
        id=str(uuid.uuid4()), price=1.0, pack_size=1, raffle_id=raffle_to_delete.id
    )
    await add_object_to_db(typeticket_to_delete)

    ticket = models_raffle.Tickets(
        id=str(uuid.uuid4()),
        type_id=typeticket.id,
        user_id=student_user.id,
    )
    await add_object_to_db(ticket)

    lot = models_raffle.Lots(
        id=str(uuid.uuid4()),
        raffle_id=raffle.id,
        description="Description of the lot",
        name="Name of the lot",
        quantity=1,
    )
    await add_object_to_db(lot)

    cash = models_raffle.Cash(user_id=student_user.id, balance=66)
    await add_object_to_db(cash)


def test_get_raffles():
    token = create_api_access_token(student_user)

    response = client.get(
        "/tombola/raffles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_raffle():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/raffles",
        json={
            "name": "test",
            "status": RaffleStatusType.creation,
            "group_id": GroupType.soli,
            "description": "Raffle's description",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_raffle():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/raffles/{raffle_to_delete.id}",
        json={
            "name": "testupdate",
            "status": RaffleStatusType.open,
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
    assert modified_raffle["status"] == RaffleStatusType.open


def test_delete_raffle():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/raffles/{raffle_to_delete.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_raffle_stats():
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/raffle/{raffle.id}/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["amount_raised"] == 1.0


# # tickets
def test_get_tickets():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_tickets_by_raffle_id():
    token = create_api_access_token(soli_user)

    response = client.get(
        f"/tombola/raffle/{raffle.id}/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_tickets_by_user_id():
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/users/{student_user.id}/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_buy_tickets():
    # Enable Redis client for locker
    change_redis_client_status(activated=True)

    token = create_api_access_token(student_user)

    response = client.post(
        f"/tombola/tickets/buy/{typeticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Disable Redis client (to avoid rate-limit)
    change_redis_client_status(activated=False)
    assert response.status_code == 201


# def test_edit_tickets():
#     token = create_api_access_token(soli_user)

#     response = client.patch(
#         f"/tombola/tickets/{ticket.id}",
#         json={
#             "user_id": soli_user.id,
#             "raffle_id": raffle.id,
#             "type_id": typeticket.id,
#             "winning_lot": None,
#             "nb_tickets": 10,
#         },
#         headers={"Authorization": f"Bearer {token}"},
#     )
#     assert response.status_code == 204


# def test_delete_tickets():
#     token = create_api_access_token(soli_user)

#     response = client.delete(
#         f"/tombola/tickets/{ticket.id}",
#         headers={"Authorization": f"Bearer {token}"},
#     )
#     assert response.status_code == 204


# # type_tickets
def test_get_typetickets():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/type_tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_typetickets_by_raffle_id():
    token = create_api_access_token(soli_user)

    response = client.get(
        f"/tombola/raffle/{raffle.id}/type_tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_typetickets():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/type_tickets",
        json={
            "raffle_id": raffle.id,
            "price": 1.23,
            "pack_size": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_typetickets():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/type_tickets/{typeticket.id}",
        json={
            "raffle_id": raffle.id,
            "price": 10.0,
            "pack_size": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_typetickets():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/type_tickets/{typeticket_to_delete.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


# # lots
def test_get_lots():
    token = create_api_access_token(student_user)

    response = client.get(
        "/tombola/lots",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_lots_by_raffle_id():
    token = create_api_access_token(student_user)

    response = client.get(
        f"/tombola/raffle/{raffle.id}/lots",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() != []


def test_draw_lots():
    token = create_api_access_token(soli_user)

    response = client.post(
        f"/tombola/lots/{lot.id}/draw",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tickets = response.json()
    assert tickets[0]["lot"] is not None


def test_create_lots():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/lots",
        json={
            "raffle_id": raffle.id,
            "description": "Lots description",
            "name": "Lots name",
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_lots():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/lots/{lot.id}",
        json={
            "raffle_id": raffle.id,
            "description": "Lots description updated",
            "name": "Lots name",
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_lots():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/lots/{lot.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

import uuid

from app.dependencies import get_settings
from app.main import app
from app.models import models_core, models_raffle
from app.utils.types.groups_type import GroupType
from app.utils.types.raffle_types import RaffleStatusType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

soli_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None
raffle: models_raffle.Raffle | None = None
typeticket: models_raffle.TypeTicket | None = None
lot: models_raffle.Lots | None = None
ticket: models_raffle.Tickets | None = None
cash: models_raffle.Cash | None = None


settings = app.dependency_overrides.get(get_settings, get_settings)()


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global soli_user, student_user, raffle, typeticket, ticket, lot, cash

    async with TestingSessionLocal() as db:
        soli_user = await create_user_with_groups([GroupType.soli], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        raffle = models_raffle.Raffle(
            id=str(uuid.uuid4()),
            name="The best raffle",
            status=RaffleStatusType.creation,
            group_id="123",
        )
        db.add(raffle)
        typeticket = models_raffle.TypeTicket(
            id=str(uuid.uuid4()), price=1.0, value=1, raffle_id=raffle.id
        )
        db.add(typeticket)

        ticket = models_raffle.Tickets(
            id=str(uuid.uuid4()),
            nb_tickets=3,
            raffle_id=raffle.id,
            group_id=raffle.group_id,
            type_id=typeticket.id,
            user_id=student_user.id,
            unit_price=typeticket.price,
        )
        db.add(ticket)

        lot = models_raffle.Lots(
            id=str(uuid.uuid4()),
            raffle_id=raffle.id,
            description="Description of the lot",
            name="Name of the lot",
            quantity=3,
        )
        db.add(lot)

        cash = models_raffle.Cash(user_id=student_user.id, balance=66)
        db.add(cash)

        await db.commit()


# raffles
def test_create_raffle():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/raffles",
        json={
            "name": "test",
            "status": RaffleStatusType.creation,
            "group_id": "1234",
            "description": "Raffle's description",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_raffles():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/raffles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_edit_raffle():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/raffles/{raffle.id}",
        json={
            "name": "testupdate",
            "status": RaffleStatusType.creation,
            "group_id": "1234",
            "description": "Raffle's description",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_raffle():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/raffles/{raffle.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


# type_tickets
def test_create_typetickets():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/type_tickets",
        json={
            "raffle_id": raffle.id,
            "price": 1.23,
            "value": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_typetickets():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/type_tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_edit_typetickets():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/type_tickets/{typeticket.id}",
        json={
            "raffle_id": raffle.id,
            "price": 10.0,
            "value": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_typetickets():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/type_tickets/{typeticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


# lots
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


def test_get_lots():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/lots",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


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


# tickets
def test_create_tickets():
    token = create_api_access_token(soli_user)

    response = client.post(
        "/tombola/tickets",
        json={
            "user_id": soli_user.id,
            "raffle_id": raffle.id,
            "type_id": typeticket.id,
            "winning_lot": None,
            "nb_tickets": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_tickets():
    token = create_api_access_token(soli_user)

    response = client.get(
        "/tombola/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_edit_tickets():
    token = create_api_access_token(soli_user)

    response = client.patch(
        f"/tombola/tickets/{ticket.id}",
        json={
            "user_id": soli_user.id,
            "raffle_id": raffle.id,
            "type_id": typeticket.id,
            "winning_lot": None,
            "nb_tickets": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_tickets():
    token = create_api_access_token(soli_user)

    response = client.delete(
        f"/tombola/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

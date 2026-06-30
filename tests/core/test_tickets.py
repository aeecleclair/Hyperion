import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.associations.models_associations import CoreAssociation
from app.core.feed import models_feed, types_feed
from app.core.groups.groups_type import GroupType
from app.core.memberships import models_memberships
from app.core.mypayment import models_mypayment
from app.core.mypayment.types_mypayment import WalletType
from app.core.tickets import models_tickets, utils_tickets
from app.core.tickets.endpoints_tickets import TicketsPermissions
from app.core.tickets.types_tickets import AnswerType
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
    get_TestingSessionLocal,
)

user: models_users.CoreUser
user_token: str

membership: models_memberships.CoreAssociationMembership
structure_manager_user: models_users.CoreUser
structure: models_mypayment.Structure
wallet: models_mypayment.Wallet
core_association: CoreAssociation
store: models_mypayment.Store

seller_can_manage_event_user: models_users.CoreUser
seller_can_manage_event_user_token: str


global_event: models_tickets.TicketEvent
event_session: models_tickets.EventSession
event_category: models_tickets.Category
free_event_category: models_tickets.Category
event_disabled_category: models_tickets.Category
event_disabled_session: models_tickets.EventSession

event_sold_out_category: models_tickets.Category
event_sold_out_session: models_tickets.EventSession
global_event_optionnal_question_id: uuid.UUID
global_event_disabled_question_id: uuid.UUID


sold_out_event: models_tickets.TicketEvent
session_sold_out_event: models_tickets.EventSession
category_sold_out_event: models_tickets.Category
ticket_sold_out_event: models_tickets.Checkout

ticket_for_user_with_answer: models_tickets.Checkout

event_linked_to_feed: models_tickets.TicketEvent


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global user, user_token
    ticket_permission_group = await create_groups_with_permissions(
        [TicketsPermissions.access_tickets],
        "ticket_permission_group",
    )
    user = await create_user_with_groups(groups=[ticket_permission_group.id])
    user_token = create_api_access_token(user)

    global \
        membership, \
        structure_manager_user, \
        structure, \
        wallet, \
        core_association, \
        store
    membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="Test Membership",
        manager_group_id=GroupType.admin,
    )
    await add_object_to_db(membership)
    structure_manager_user = await create_user_with_groups(groups=[])
    structure = models_mypayment.Structure(
        id=uuid.uuid4(),
        short_id="test",
        name="Test Structure",
        siege_address_street="123 Test Street",
        siege_address_city="Test City",
        siege_address_zipcode="12345",
        siege_address_country="Test Country",
        siret=None,
        iban="FR",
        bic="",
        manager_user_id=structure_manager_user.id,
        creation=datetime.now(tz=UTC),
        association_membership_id=membership.id,
    )
    await add_object_to_db(structure)
    wallet = models_mypayment.Wallet(
        id=uuid.uuid4(),
        type=WalletType.STORE,
        balance=0,
    )
    await add_object_to_db(wallet)
    core_association = CoreAssociation(
        id=uuid.uuid4(),
        name="Test Association",
        group_id=GroupType.admin,
    )
    await add_object_to_db(core_association)
    store = models_mypayment.Store(
        id=uuid.uuid4(),
        name="Test Store",
        structure_id=structure.id,
        wallet_id=wallet.id,
        creation=datetime.now(tz=UTC),
        association_id=core_association.id,
    )
    await add_object_to_db(store)

    global seller_can_manage_event_user, seller_can_manage_event_user_token
    seller_can_manage_event_user = await create_user_with_groups(groups=[])
    seller_can_manage_event_user_token = create_api_access_token(
        seller_can_manage_event_user,
    )
    seller = models_mypayment.Seller(
        store_id=store.id,
        user_id=seller_can_manage_event_user.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
        can_manage_events=True,
    )
    await add_object_to_db(seller)

    global global_event, event_session, event_category, free_event_category

    ticket_event_id = uuid.uuid4()
    event_session = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=ticket_event_id,
        name="Test Session",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=None,
        disabled=False,
    )
    event_category = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=ticket_event_id,
        name="Test Category",
        quota=None,
        disabled=False,
        price=1000,
        required_membership=None,
    )
    free_event_category = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=ticket_event_id,
        name="Test Free Category",
        quota=None,
        disabled=False,
        price=0,
        required_membership=None,
    )

    global event_disabled_category, event_disabled_session
    event_disabled_category = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=ticket_event_id,
        name="Test Disabled Category",
        quota=None,
        disabled=True,
        price=1000,
        required_membership=None,
    )
    event_disabled_session = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=ticket_event_id,
        name="Test Disabled Session",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=None,
        disabled=True,
    )

    global global_event_optionnal_question_id, global_event_disabled_question_id
    global_event_optionnal_question_id = uuid.uuid4()
    global_event_disabled_question_id = uuid.uuid4()
    global_event = models_tickets.TicketEvent(
        id=uuid.uuid4(),
        store_id=store.id,
        name="Test global_event",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=False,
        sessions=[event_session, event_disabled_session],
        categories=[event_category, event_disabled_category, free_event_category],
        questions=[
            models_tickets.Question(
                id=global_event_optionnal_question_id,
                event_id=ticket_event_id,
                question="Test Question",
                required=False,
                answer_type=AnswerType.TEXT,
                price=100,
                disabled=False,
            ),
            models_tickets.Question(
                id=global_event_disabled_question_id,
                event_id=ticket_event_id,
                question="Test Disabled Question",
                required=False,
                answer_type=AnswerType.TEXT,
                price=100,
                disabled=True,
            ),
        ],
    )
    await add_object_to_db(global_event)

    global event_sold_out_category, event_sold_out_session
    event_sold_out_category = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test global_event Sold Out Category",
        quota=1,
        disabled=False,
        price=1000,
        required_membership=None,
    )
    await add_object_to_db(event_sold_out_category)
    ticket_sold_out_category = models_tickets.Checkout(
        id=uuid.uuid4(),
        category_id=event_sold_out_category.id,
        session_id=event_session.id,
        event_id=global_event.id,
        user_id=user.id,
        price=10,
        scanned=False,
        paid=True,
        expiration=datetime.now(tz=UTC) + timedelta(hours=1),
        answers=[],
    )
    await add_object_to_db(ticket_sold_out_category)
    event_sold_out_session = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test global_event Sold Out Session",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=1,
        disabled=False,
    )
    await add_object_to_db(event_sold_out_session)
    ticket_sold_out_session = models_tickets.Checkout(
        id=uuid.uuid4(),
        category_id=event_category.id,
        session_id=event_sold_out_session.id,
        event_id=global_event.id,
        user_id=user.id,
        price=10,
        scanned=False,
        paid=True,
        expiration=datetime.now(tz=UTC) + timedelta(hours=1),
        answers=[],
    )
    await add_object_to_db(ticket_sold_out_session)

    global \
        sold_out_event, \
        session_sold_out_event, \
        category_sold_out_event, \
        ticket_sold_out_event
    ticket_sold_out_event_id = uuid.uuid4()
    session_sold_out_event = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=ticket_sold_out_event_id,
        name="Test Session Sold Out",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=1,
        disabled=False,
    )
    category_sold_out_event = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=ticket_sold_out_event_id,
        name="Test Category Sold Out",
        quota=1,
        disabled=False,
        price=1000,
        required_membership=None,
    )
    sold_out_event = models_tickets.TicketEvent(
        id=ticket_sold_out_event_id,
        store_id=store.id,
        name="Test global_event Sold Out",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=1,
        disabled=False,
        sessions=[session_sold_out_event],
        categories=[category_sold_out_event],
        questions=[],
    )
    await add_object_to_db(sold_out_event)
    user_for_sold_out_ticket = await create_user_with_groups(groups=[])
    ticket_sold_out_event = models_tickets.Checkout(
        id=uuid.uuid4(),
        category_id=category_sold_out_event.id,
        session_id=session_sold_out_event.id,
        event_id=ticket_sold_out_event_id,
        user_id=user_for_sold_out_ticket.id,
        price=10,
        scanned=False,
        paid=True,
        expiration=datetime.now(tz=UTC) + timedelta(hours=1),
        answers=[],
    )
    await add_object_to_db(ticket_sold_out_event)

    global ticket_for_user_with_answer
    ticket_for_user_with_answer_id = uuid.uuid4()
    ticket_for_user_with_answer = models_tickets.Checkout(
        id=ticket_for_user_with_answer_id,
        category_id=event_category.id,
        session_id=event_session.id,
        event_id=global_event.id,
        user_id=user.id,
        price=10,
        scanned=False,
        paid=True,
        expiration=datetime.now(tz=UTC) - timedelta(hours=1),
        answers=[
            models_tickets.Answer(
                id=uuid.uuid4(),
                checkout_id=ticket_for_user_with_answer_id,
                question_id=global_event_optionnal_question_id,
                answer="Test Answer",
            ),
        ],
    )
    await add_object_to_db(ticket_for_user_with_answer)

    global event_linked_to_feed
    event_linked_to_feed = models_tickets.TicketEvent(
        id=uuid.uuid4(),
        store_id=store.id,
        name="Test Event Linked to Feed",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=False,
        sessions=[],
        categories=[],
        questions=[],
    )
    await add_object_to_db(event_linked_to_feed)
    feed = models_feed.News(
        id=uuid.uuid4(),
        title="Test Feed News",
        module="tickets",
        module_object_id=event_linked_to_feed.id,
        start=datetime.now(tz=UTC) - timedelta(days=1),
        end=datetime.now(tz=UTC) + timedelta(days=1),
        entity="Test Entity",
        location="Test Location",
        action_start=datetime.now(tz=UTC) - timedelta(days=1),
        image_directory="test_directory",
        image_id=uuid.uuid4(),
        status=types_feed.NewsStatus.PUBLISHED,
    )
    await add_object_to_db(feed)


async def test_payment_callback(client: TestClient):
    async with get_TestingSessionLocal()() as db:
        await utils_tickets.mypayment_callback_callback(
            checkout_id=ticket_for_user_with_answer.id,
            db=db,
        )


def test_get_open_events(client: TestClient):
    response = client.get(
        "/tickets/events",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) > 1


def test_get_event_with_non_existing_id(client: TestClient):
    response = client.get(
        f"/tickets/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


async def test_get_event_disabled(client: TestClient):
    event = models_tickets.TicketEvent(
        id=uuid.uuid4(),
        store_id=store.id,
        name="Test Disabled Event",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=True,
        sessions=[],
        categories=[],
        questions=[],
    )
    await add_object_to_db(event)
    response = client.get(
        f"/tickets/events/{event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Event is disabled"


def test_get_event(client: TestClient):
    response = client.get(
        f"/tickets/events/{global_event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    event = response.json()
    assert event["id"] == str(global_event.id)
    assert len(event["sessions"]) > 0
    assert len(event["categories"]) > 0
    assert event["sold_out"] is False


def test_get_sold_out_event(client: TestClient):
    response = client.get(
        f"/tickets/events/{sold_out_event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    event = response.json()
    assert event["id"] == str(sold_out_event.id)
    assert len(event["sessions"]) > 0
    assert len(event["categories"]) > 0
    assert event["sold_out"] is True


def test_create_checkout_with_invalid_category(client: TestClient):
    response = client.post(
        f"/tickets/events/{sold_out_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(uuid.uuid4()),
            "session_id": str(session_sold_out_event.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_create_checkout_with_disabled_category(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_disabled_category.id),
            "session_id": str(event_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Category is disabled"


def test_create_checkout_with_invalid_session(client: TestClient):
    response = client.post(
        f"/tickets/events/{sold_out_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_sold_out_event.id),
            "session_id": str(uuid.uuid4()),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_create_checkout_with_disabled_session(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_disabled_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Session is disabled"


async def test_create_checkout_with_disabled_event(client: TestClient):
    event_id = uuid.uuid4()
    category_id = uuid.uuid4()
    session_id = uuid.uuid4()
    event = models_tickets.TicketEvent(
        id=event_id,
        store_id=store.id,
        name="Test Disabled Event",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=True,
        sessions=[
            models_tickets.EventSession(
                id=session_id,
                event_id=event_id,
                name="Test Session",
                start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
                quota=None,
                disabled=False,
            ),
        ],
        categories=[
            models_tickets.Category(
                id=category_id,
                event_id=event_id,
                name="Test Category",
                quota=None,
                disabled=False,
                price=1000,
                required_membership=None,
            ),
        ],
        questions=[],
    )
    await add_object_to_db(event)
    response = client.post(
        f"/tickets/events/{event_id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_id),
            "session_id": str(session_id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Event is disabled"


async def test_create_checkout_with_not_open_event(client: TestClient):
    event_id = uuid.uuid4()
    category_id = uuid.uuid4()
    session_id = uuid.uuid4()
    event = models_tickets.TicketEvent(
        id=event_id,
        store_id=store.id,
        name="Test Disabled Event",
        open_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=2),
        quota=10,
        disabled=False,
        sessions=[
            models_tickets.EventSession(
                id=session_id,
                event_id=event_id,
                name="Test Session",
                start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
                quota=None,
                disabled=False,
            ),
        ],
        categories=[
            models_tickets.Category(
                id=category_id,
                event_id=event_id,
                name="Test Category",
                quota=None,
                disabled=False,
                price=1000,
                required_membership=None,
            ),
        ],
        questions=[],
    )
    await add_object_to_db(event)
    response = client.post(
        f"/tickets/events/{event_id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_id),
            "session_id": str(session_id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Event is not open yet"


async def test_create_checkout_with_closed_event(client: TestClient):
    event_id = uuid.uuid4()
    category_id = uuid.uuid4()
    session_id = uuid.uuid4()
    event = models_tickets.TicketEvent(
        id=event_id,
        store_id=store.id,
        name="Test Disabled Event",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=2),
        close_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=10,
        disabled=False,
        sessions=[
            models_tickets.EventSession(
                id=session_id,
                event_id=event_id,
                name="Test Session",
                start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
                quota=None,
                disabled=False,
            ),
        ],
        categories=[
            models_tickets.Category(
                id=category_id,
                event_id=event_id,
                name="Test Category",
                quota=None,
                disabled=False,
                price=1000,
                required_membership=None,
            ),
        ],
        questions=[],
    )
    await add_object_to_db(event)
    response = client.post(
        f"/tickets/events/{event_id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_id),
            "session_id": str(session_id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Event is closed"


def test_create_checkout_with_category_from_another_event(client: TestClient):
    response = client.post(
        f"/tickets/events/{sold_out_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(session_sold_out_event.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Category does not belong to the event"


def test_create_checkout_with_session_from_another_event(client: TestClient):
    response = client.post(
        f"/tickets/events/{sold_out_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_sold_out_event.id),
            "session_id": str(event_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Session does not belong to the event"


def test_create_checkout_with_sold_out_event(client: TestClient):
    response = client.post(
        f"/tickets/events/{sold_out_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(category_sold_out_event.id),
            "session_id": str(session_sold_out_event.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Event is sold out"


def test_create_checkout_with_sold_out_category(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_sold_out_category.id),
            "session_id": str(event_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Category is sold out"


def test_create_checkout_with_sold_out_session(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_sold_out_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Session is sold out"


async def test_create_checkout_with_missing_membership(client: TestClient):
    event_with_required_membership_session_id = uuid.uuid4()
    event_with_required_membership_category_id = uuid.uuid4()
    event_with_required_membership_id = uuid.uuid4()
    event_with_required_membership = models_tickets.TicketEvent(
        id=event_with_required_membership_id,
        store_id=store.id,
        name="Test Event with Required Membership",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=False,
        sessions=[
            models_tickets.EventSession(
                id=event_with_required_membership_session_id,
                event_id=event_with_required_membership_id,
                name="Test Session",
                start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
                quota=None,
                disabled=False,
            ),
        ],
        categories=[
            models_tickets.Category(
                id=event_with_required_membership_category_id,
                event_id=event_with_required_membership_id,
                name="Test Category",
                quota=None,
                disabled=False,
                price=1000,
                required_membership=membership.id,
            ),
        ],
        questions=[],
    )
    await add_object_to_db(event_with_required_membership)
    response = client.post(
        f"/tickets/events/{event_with_required_membership_id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_with_required_membership_category_id),
            "session_id": str(event_with_required_membership_session_id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "User does not have required membership to choose this category"
    )


def test_create_checkout_with_answer_present_multiple_times(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_sold_out_session.id),
            "answers": [
                {
                    "question_id": str(global_event_optionnal_question_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer",
                    },
                },
                {
                    "question_id": str(global_event_optionnal_question_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer 2",
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"Question with id {global_event_optionnal_question_id} is answered multiple times"
    )


def test_create_checkout_with_invalid_question_id(client: TestClient):
    invalid_id = uuid.uuid4()

    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_sold_out_session.id),
            "answers": [
                {
                    "question_id": str(invalid_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer",
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"Question with id {invalid_id} not found for this event"
    )


def test_create_checkout_with_disabled_question(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_sold_out_session.id),
            "answers": [
                {
                    "question_id": str(global_event_disabled_question_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer",
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"Question with id {global_event_disabled_question_id} is disabled"
    )


def test_create_checkout_with_invalid_answer_type(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_sold_out_session.id),
            "answers": [
                {
                    "question_id": str(global_event_optionnal_question_id),
                    "answer": {
                        "answer_type": "number",
                        "answer": 3,
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"Answer type for question with id {global_event_optionnal_question_id} should be text"
    )


async def test_create_checkout_with_missing_required_question(client: TestClient):
    event_with_required_question_session_id = uuid.uuid4()
    event_with_required_question_category_id = uuid.uuid4()
    event_with_required_question_id = uuid.uuid4()
    question_id = uuid.uuid4()

    event_with_required_question = models_tickets.TicketEvent(
        id=event_with_required_question_id,
        store_id=store.id,
        name="Test Event with Required question",
        open_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        close_datetime=datetime.now(tz=UTC) + timedelta(days=1),
        quota=10,
        disabled=False,
        sessions=[
            models_tickets.EventSession(
                id=event_with_required_question_session_id,
                event_id=event_with_required_question_id,
                name="Test Session",
                start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
                quota=None,
                disabled=False,
            ),
        ],
        categories=[
            models_tickets.Category(
                id=event_with_required_question_category_id,
                event_id=event_with_required_question_id,
                name="Test Category",
                quota=None,
                disabled=False,
                price=1000,
                required_membership=None,
            ),
        ],
        questions=[
            models_tickets.Question(
                id=question_id,
                event_id=event_with_required_question_id,
                question="Test Question",
                answer_type=AnswerType.TEXT,
                price=None,
                required=True,
                disabled=False,
            ),
        ],
    )
    await add_object_to_db(event_with_required_question)

    response = client.post(
        f"/tickets/events/{event_with_required_question_id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_with_required_question_category_id),
            "session_id": str(event_with_required_question_session_id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == f"Answers for questions {question_id} are required"
    )


def test_create_checkout(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(event_category.id),
            "session_id": str(event_session.id),
            "answers": [
                {
                    "question_id": str(global_event_optionnal_question_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer",
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    # TODO
    # assert response.json() == ""
    assert response.status_code == 201
    # Price of the event + price of the optionnal question
    assert response.json()["price"] == 1000 + 100


def test_create_checkout_for_free_event(client: TestClient):
    response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(free_event_category.id),
            "session_id": str(event_session.id),
            "answers": [],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    # TODO
    # assert response.json() == ""
    assert response.status_code == 201
    # Price of the event + price of the optionnal question
    assert response.json()["price"] == 0


def test_get_user_tickets(client: TestClient):
    response = client.get(
        "/tickets/user/me/tickets",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) > 1
    ticket = next(
        (t for t in tickets if t["id"] == str(ticket_for_user_with_answer.id)),
        None,
    )
    assert ticket is not None
    assert len(ticket["answers"]) > 0


# ticket_request_change_over


async def test_ticket_request_change_over_for_non_existing_ticket(client: TestClient):
    response = client.post(
        "/tickets/user/me/tickets/change-over/request",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "ticket_id": str(uuid.uuid4()),
            "email": "test@test.fr",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


async def test_ticket_request_change_over_for_ticket_from_different_user(
    client: TestClient,
):
    response = client.post(
        "/tickets/user/me/tickets/change-over/request",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "ticket_id": str(ticket_sold_out_event.id),
            "email": "test@test.fr",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the owner of the ticket"


async def test_ticket_request_change_over_for_ticket_for_non_existing_user_email(
    client: TestClient,
):
    response = client.post(
        "/tickets/user/me/tickets/change-over/request",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "ticket_id": str(ticket_for_user_with_answer.id),
            "email": "non-existing@test.fr",
        },
    )
    assert response.status_code == 204


async def test_ticket_request_change_over(
    client: TestClient,
    mocker: MockerFixture,
):
    ticket_to_transfer = models_tickets.Checkout(
        id=uuid.uuid4(),
        category_id=event_category.id,
        session_id=event_session.id,
        event_id=global_event.id,
        user_id=user.id,
        price=10,
        scanned=False,
        paid=True,
        expiration=datetime.now(tz=UTC) + timedelta(hours=1),
        answers=[],
    )
    await add_object_to_db(ticket_to_transfer)

    generate_token_patch = mocker.patch(
        "app.core.tickets.endpoints_tickets.security.generate_token",
        return_value="token",
    )

    response = client.post(
        "/tickets/user/me/tickets/change-over/request",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "ticket_id": str(ticket_to_transfer.id),
            "email": seller_can_manage_event_user.email,
        },
    )
    assert response.status_code == 204
    generate_token_patch.assert_called()

    response = client.get(
        "/tickets/user/me/tickets/change-over/accept?token=token",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert "message?type=ticket_change_over_success" in response.headers["location"]


# ticket_accept_change_over


def test_ticket_accept_change_over_with_invalid_token(client: TestClient):
    response = client.get(
        "/tickets/user/me/tickets/change-over/accept?token=invalid_token",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "message?type=ticket_change_over_invalid" in response.headers["location"]


# get_event_admin


def test_get_event_admin_invalid_event_id(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_get_event_admin_as_non_authorised_seller(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_get_event_admin(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{sold_out_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200
    event = response.json()
    assert event["id"] == str(sold_out_event.id)
    assert len(event["sessions"]) > 0
    assert len(event["categories"]) > 0
    assert event["tickets_sold"] == 1
    assert event["tickets_in_checkout"] == 0


# create_event


def test_create_event_as_non_authorised_seller(client: TestClient):
    response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 10,
            "sessions": [],
            "categories": [],
            "questions": [],
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_create_event_without_sessions(client: TestClient):
    response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 11,
            "sessions": [],
            "categories": [
                {
                    "name": "Test Category",
                    "price": 1000,
                    "quota": 10,
                    "required_membership": None,
                },
            ],
            "questions": [],
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Event must have at least one session and one category"
    )


def test_create_event_with_category_price_to_low(client: TestClient):
    response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 11,
            "sessions": [
                {
                    "name": "Test Session",
                    "start_datetime": (
                        datetime.now(tz=UTC) + timedelta(days=1)
                    ).isoformat(),
                    "quota": 10,
                },
            ],
            "categories": [
                {
                    "name": "Test Category",
                    "price": 10,
                    "quota": 10,
                    "required_membership": None,
                },
            ],
            "questions": [],
        },
    )
    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, Price must be zero or greater than one euro"
    )


def test_create_event(client: TestClient):
    response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 11,
            "sessions": [
                {
                    "name": "Test Session",
                    "start_datetime": (
                        datetime.now(tz=UTC) + timedelta(days=1)
                    ).isoformat(),
                    "quota": 10,
                },
            ],
            "categories": [
                {
                    "name": "Test Category",
                    "price": 1000,
                    "quota": 10,
                    "required_membership": None,
                },
            ],
            "questions": [
                {
                    "id": str(global_event_optionnal_question_id),
                    "question": "Test Question",
                    "required": False,
                    "answer_type": "text",
                    "price": 1000,
                },
            ],
        },
    )
    assert response.status_code == 201
    event = response.json()
    assert len(event["sessions"]) == 1
    assert len(event["categories"]) == 1
    assert event["quota"] == 11
    assert event["tickets_sold"] == 0
    assert event["tickets_in_checkout"] == 0


# update_event


def test_update_event_non_existing_event(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Event",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_update_event_as_non_authorised_seller(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "Updated Test Event",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_update_event(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Event",
        },
    )
    assert response.status_code == 204


def test_update_event_disable(client: TestClient):
    create_response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event To Disable",
            "open_datetime": (datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 10,
            "sessions": [
                {
                    "name": "Test Session",
                    "start_datetime": (
                        datetime.now(tz=UTC) + timedelta(days=1)
                    ).isoformat(),
                    "quota": 10,
                },
            ],
            "categories": [
                {
                    "name": "Test Category",
                    "price": 1000,
                    "quota": 10,
                    "required_membership": None,
                },
            ],
            "questions": [],
        },
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["id"]

    response = client.patch(
        f"/tickets/admin/events/{event_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "disabled": True,
        },
    )
    assert response.status_code == 204

    admin_response = client.get(
        f"/tickets/admin/events/{event_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["disabled"] is True

    public_response = client.get(
        f"/tickets/events/{event_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert public_response.status_code == 400
    assert public_response.json()["detail"] == "Event is disabled"

    open_events_response = client.get(
        "/tickets/events",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert open_events_response.status_code == 200
    assert event_id not in {event["id"] for event in open_events_response.json()}


# create_session


def test_create_session_with_non_existing_event(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{uuid.uuid4()}/sessions/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Test Session",
            "start_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "quota": 10,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_create_session_as_non_authorised_seller(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/sessions/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "Test Session",
            "start_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "quota": 10,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_create_session(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/sessions/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Test Session",
            "start_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "quota": 10,
        },
    )
    assert response.status_code == 201
    session = response.json()
    assert session["name"] == "Test Session"
    assert session["quota"] == 10
    assert session["event_id"] == str(global_event.id)


# update_session


def test_update_session_with_non_existing_event(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{uuid.uuid4()}/sessions/{event_session.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Session",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_update_session_as_non_authorised_seller(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/sessions/{event_session.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "Updated Test Session",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_update_session_with_non_existing_session(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/sessions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Session",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


async def test_update_session(client: TestClient):
    session_without_tickets = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test Session without tickets",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=None,
        disabled=True,
    )
    await add_object_to_db(session_without_tickets)
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/sessions/{session_without_tickets.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Session",
            "disabled": True,
        },
    )
    assert response.status_code == 204


# create_category


def test_create_category_with_non_existing_event(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{uuid.uuid4()}/categories/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Test Category",
            "price": 1000,
            "quota": 10,
            "required_membership": None,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_create_category_as_non_authorised_seller(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/categories/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "Test Category",
            "price": 1000,
            "quota": 10,
            "required_membership": None,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_create_category_with_price_to_low(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/categories/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Test Category",
            "price": 10,
            "quota": 10,
            "required_membership": None,
        },
    )
    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, Price must be zero or greater than one euro"
    )


def test_create_category(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/categories/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Test Category",
            "price": 1000,
            "quota": 10,
            "required_membership": None,
        },
    )
    assert response.status_code == 201
    category = response.json()
    assert category["name"] == "Test Category"
    assert category["price"] == 1000
    assert category["quota"] == 10


# create_question


def test_create_question_with_non_existing_event(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{uuid.uuid4()}/questions/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Test Question",
            "answer_type": "text",
            "price": 100,
            "required": False,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_create_question_as_non_authorised_seller(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/questions/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "question": "Test Question",
            "answer_type": "text",
            "price": 100,
            "required": False,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_create_question(client: TestClient):
    response = client.post(
        f"/tickets/admin/events/{global_event.id}/questions/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "New Test Question",
            "answer_type": "text",
            "price": 100,
            "required": True,
        },
    )
    assert response.status_code == 201
    question = response.json()
    assert question["question"] == "New Test Question"
    assert question["answer_type"] == "text"
    assert question["price"] == 100
    assert question["required"] is True
    assert question["disabled"] is False
    assert question["event_id"] == str(global_event.id)


# update_category


def test_update_category_with_non_existing_event(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{uuid.uuid4()}/categories/{event_category.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Category",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_update_category_as_non_authorised_seller(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/categories/{event_category.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "Updated Test Category",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_update_category_with_non_existing_category(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/categories/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Category",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_update_category_price_with_existing_tickets(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/categories/{event_category.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Category",
            "price": 2000,
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cannot update category price or required_membership with checkouts or tickets"
    )


async def test_update_category_with_price_to_low(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/categories/{event_category.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Category",
            "price": 10,
        },
    )
    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, Price must be zero or greater than one euro"
    )


async def test_update_category(client: TestClient):
    category_without_tickets = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test Category without tickets",
        quota=None,
        disabled=False,
        price=1000,
        required_membership=None,
    )
    await add_object_to_db(category_without_tickets)
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/categories/{category_without_tickets.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "name": "Updated Test Category",
            "disabled": True,
        },
    )
    assert response.status_code == 204


# update_question


def test_update_question_with_non_existing_event(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{uuid.uuid4()}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Updated Test Question",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_update_question_as_non_authorised_seller(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "question": "Updated Test Question",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_update_question_with_non_existing_question(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Updated Test Question",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Question not found"


async def test_update_question_answer_type_with_answer(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Updated Test Question",
            "answer_type": "number",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cannot update answer_type or price for question with answers"
    )


async def test_update_question_price_with_answer(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Updated Test Question",
            "price": 100,
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cannot update answer_type or price for question with answers"
    )


def test_update_question_disable_with_answers(client: TestClient):
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "disabled": True,
            "question": "Updated Test Question",
        },
    )
    assert response.status_code == 204

    checkout_response = client.post(
        f"/tickets/events/{global_event.id}/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "category_id": str(free_event_category.id),
            "session_id": str(event_session.id),
            "answers": [
                {
                    "question_id": str(global_event_optionnal_question_id),
                    "answer": {
                        "answer_type": "text",
                        "answer": "Test Answer",
                    },
                },
            ],
            "mypayment_request_method": "transfer_request",
            "mypayment_transfer_redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert checkout_response.status_code == 400
    assert (
        checkout_response.json()["detail"]
        == f"Question with id {global_event_optionnal_question_id} is disabled"
    )


async def test_update_question(client: TestClient):
    question_without_tickets = models_tickets.Question(
        id=uuid.uuid4(),
        event_id=global_event.id,
        question="Test Question without tickets",
        answer_type=AnswerType.TEXT,
        price=None,
        required=False,
        disabled=False,
    )
    await add_object_to_db(question_without_tickets)
    response = client.patch(
        f"/tickets/admin/events/{global_event.id}/questions/{question_without_tickets.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "question": "Updated Test Question",
        },
    )
    assert response.status_code == 204


# delete_event


def test_delete_event_not_found(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_delete_event_as_non_authorised_seller(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_delete_event_with_checkouts_or_tickets(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete event with checkouts or tickets"


def test_delete_event_linked_to_feed(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{event_linked_to_feed.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete event linked to the feed"


def test_delete_event(client: TestClient):
    create_response = client.post(
        "/tickets/admin/events/",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
        json={
            "store_id": str(store.id),
            "name": "Test Event To Delete",
            "open_datetime": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
            "close_datetime": (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
            "quota": 10,
            "sessions": [
                {
                    "name": "Test Session",
                    "start_datetime": (
                        datetime.now(tz=UTC) + timedelta(days=1)
                    ).isoformat(),
                    "quota": 10,
                },
            ],
            "categories": [
                {
                    "name": "Test Category",
                    "price": 1000,
                    "quota": 10,
                    "required_membership": None,
                },
            ],
            "questions": [],
        },
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["id"]

    response = client.delete(
        f"/tickets/admin/events/{event_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 204

    admin_response = client.get(
        f"/tickets/admin/events/{event_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert admin_response.status_code == 404


# delete_session


def test_delete_session_with_checkouts_or_tickets(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/sessions/{event_session.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Cannot delete session with checkouts or tickets"
    )


async def test_delete_session(client: TestClient):
    session_without_tickets = models_tickets.EventSession(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test Session to delete",
        start_datetime=datetime.now(tz=UTC) - timedelta(days=1),
        quota=None,
        disabled=False,
    )
    await add_object_to_db(session_without_tickets)

    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/sessions/{session_without_tickets.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 204

    admin_response = client.get(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert admin_response.status_code == 200
    session_ids = {session["id"] for session in admin_response.json()["sessions"]}
    assert str(session_without_tickets.id) not in session_ids


# delete_category


def test_delete_category_with_checkouts_or_tickets(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/categories/{event_category.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Cannot delete category with checkouts or tickets"
    )


async def test_delete_category(client: TestClient):
    category_without_tickets = models_tickets.Category(
        id=uuid.uuid4(),
        event_id=global_event.id,
        name="Test Category to delete",
        quota=None,
        disabled=False,
        price=1000,
        required_membership=None,
    )
    await add_object_to_db(category_without_tickets)

    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/categories/{category_without_tickets.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 204

    admin_response = client.get(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert admin_response.status_code == 200
    category_ids = {category["id"] for category in admin_response.json()["categories"]}
    assert str(category_without_tickets.id) not in category_ids


# delete_question


def test_delete_question_with_answers(client: TestClient):
    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/questions/{global_event_optionnal_question_id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete question with answers"


async def test_delete_question(client: TestClient):
    question_without_answers = models_tickets.Question(
        id=uuid.uuid4(),
        event_id=global_event.id,
        question="Test Question to delete",
        answer_type=AnswerType.TEXT,
        price=None,
        required=False,
        disabled=False,
    )
    await add_object_to_db(question_without_answers)

    response = client.delete(
        f"/tickets/admin/events/{global_event.id}/questions/{question_without_answers.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 204

    admin_response = client.get(
        f"/tickets/admin/events/{global_event.id}",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert admin_response.status_code == 200
    question_ids = {question["id"] for question in admin_response.json()["questions"]}
    assert str(question_without_answers.id) not in question_ids


# get_event_tickets


def test_get_event_tickets_with_invalid_event_id(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{uuid.uuid4()}/tickets",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_get_event_tickets_as_non_authorised_seller(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{global_event.id}/tickets",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_get_event_tickets(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{global_event.id}/tickets",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) > 0
    assert tickets[0]["event_id"] == str(global_event.id)


# get_event_tickets_csv


def test_get_event_tickets_csv_with_invalid_event_id(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{uuid.uuid4()}/tickets/csv",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_get_event_tickets_csv_as_non_authorised_seller(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{global_event.id}/tickets/csv",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_get_event_tickets_csv(client: TestClient):
    response = client.get(
        f"/tickets/admin/events/{global_event.id}/tickets/csv",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200


# check_ticket


def test_check_ticket_with_invalid_ticket_id(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{uuid.uuid4()}/check",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_check_ticket_as_non_authorised_seller(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{ticket_sold_out_event.id}/check",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_check_ticket(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{ticket_sold_out_event.id}/check",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200
    checked_ticket = response.json()
    assert checked_ticket["id"] == str(ticket_sold_out_event.id)
    assert checked_ticket["scanned"] is False


# scan_ticket


def test_scan_ticket_with_invalid_ticket_id(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{uuid.uuid4()}/scan",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_scan_ticket_as_non_authorised_seller(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{ticket_sold_out_event.id}/scan",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_scan_ticket(client: TestClient):
    response = client.post(
        f"/tickets/admin/tickets/{ticket_sold_out_event.id}/scan",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 204

    response = client.post(
        f"/tickets/admin/tickets/{ticket_sold_out_event.id}/scan",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Ticket is already scanned"


# get_events_by_store


def test_get_events_by_store_with_invalid_store_id(client: TestClient):
    response = client.get(
        f"/tickets/admin/store/{uuid.uuid4()}/events",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store not found"


def test_get_events_by_store(client: TestClient):
    response = client.get(
        f"/tickets/admin/store/{store.id}/events",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) > 1


# get_events_by_association


async def test_get_events_by_association_with_no_store(client: TestClient):
    core_association = CoreAssociation(
        id=uuid.uuid4(),
        name="Test Association No Store",
        group_id=GroupType.admin,
    )
    await add_object_to_db(core_association)
    response = client.get(
        f"/tickets/admin/association/{core_association.id}/events",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No store associated with this association"


def test_get_events_by_association_as_non_authorised_seller(client: TestClient):
    response = client.get(
        f"/tickets/admin/association/{core_association.id}/events",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to manage store's events"
    )


def test_get_events_by_association(client: TestClient):
    response = client.get(
        f"/tickets/admin/association/{core_association.id}/events",
        headers={"Authorization": f"Bearer {seller_can_manage_event_user_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) > 1

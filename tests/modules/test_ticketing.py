from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.memberships import models_memberships
from app.core.mypayment import models_mypayment
from app.core.mypayment.types_mypayment import WalletType
from app.core.users import models_users
from app.modules.ticketing import models_ticketing

# We need to import event_loop for pytest-asyncio routine defined bellow
from app.modules.ticketing.endpoints_ticketing import TicketingPermissions
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
)

admin_user: models_users.CoreUser
admin_user_token: str
structure_manager_user: models_users.CoreUser
structure_manager_user_token: str

bde_group: models_groups.CoreGroup

association_membership: models_memberships.CoreAssociationMembership
association_membership_user: models_memberships.CoreAssociationUserMembership
structure: models_mypayment.Structure

store_wallet: models_mypayment.Wallet
store: models_mypayment.Store


student_user: models_users.CoreUser

event1: models_ticketing.TicketingEvent
event2: models_ticketing.TicketingEvent
event_fake: models_ticketing.TicketingEvent

student_token: str
admin_token: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global admin_user, admin_user_token
    admin_user = await create_user_with_groups(groups=[GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)

    global bde_group
    bde_group = await create_groups_with_permissions(
        [TicketingPermissions.manage_events],
        "BDE Group",
    )

    global association_membership
    association_membership = models_memberships.CoreAssociationMembership(
        id=uuid4(),
        name="Test Association Membership",
        manager_group_id=bde_group.id,
    )
    await add_object_to_db(association_membership)

    global structure_manager_user, structure_manager_user_token, structure

    structure_manager_user = await create_user_with_groups(groups=[])
    structure_manager_user_token = create_api_access_token(structure_manager_user)

    structure = models_mypayment.Structure(
        id=uuid4(),
        name="Test Structure",
        creation=datetime.now(UTC),
        association_membership_id=association_membership.id,
        manager_user_id=structure_manager_user.id,
        short_id="ABC",
        siege_address_street="123 Test Street",
        siege_address_city="Test City",
        siege_address_zipcode="12345",
        siege_address_country="Test Country",
        siret="12345678901234",
        iban="FR76 1234 5678 9012 3456 7890 123",
        bic="AZERTYUIOP",
    )
    await add_object_to_db(structure)

    # Create store
    global store_wallet, store
    store_wallet = models_mypayment.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=0,
    )
    await add_object_to_db(store_wallet)

    store = models_mypayment.Store(
        id=uuid4(),
        name="Test Store",
        structure_id=structure.id,
        wallet_id=store_wallet.id,
        creation=datetime.now(UTC),
    )
    await add_object_to_db(store)

    # Create events
    global event1, event2, event_fake
    event1 = models_ticketing.Event(
        id=uuid4(),
        name="Event 1",
        open_date=datetime(2024, 1, 1, tzinfo=UTC),
        # Tests will not pass in 2200, will MyECLPay be still around ? :D
        close_date=datetime(2200, 12, 31, tzinfo=UTC),
        quota=4,
        user_quota=2,
        used_quota=1,
        disabled=False,
        creator_id=str(admin_user.id),
        store_id=store.id,
    )
    await add_object_to_db(event1)
    # Event will be used to test disabled state etc.
    event2 = models_ticketing.TicketingEvent(
        id=uuid4(),
        name="Event 2",
        open_date=datetime(2024, 1, 1, tzinfo=UTC),
        close_date=datetime(2200, 12, 31, tzinfo=UTC),
        quota=3,
        user_quota=2,
        used_quota=1,
        disabled=False,
        creator_id=str(admin_user.id),
        store_id=store.id,
    )
    await add_object_to_db(event2)

    event_fake = models_ticketing.TicketingEvent(
        id=uuid4(),
        name="Event Fake",
        open_date=datetime(2024, 1, 1, tzinfo=UTC),
        close_date=datetime(2200, 12, 31, tzinfo=UTC),
        quota=3,
        user_quota=2,
        used_quota=1,
        disabled=False,
        creator_id=str(admin_user.id),
        store_id=store.id,
    )
    # Do not add event_fake to the database

    # Create sessions and categories for event1
    session1 = models_ticketing.TicketingSession(
        id=uuid4(),
        event_id=event1.id,
        name="Session 1",
        quota=2,
        user_quota=1,
        used_quota=1,
        disabled=False,
    )
    await add_object_to_db(session1)
    session2 = models_ticketing.Session(
        id=uuid4(),
        event_id=event1.id,
        name="Session 2",
        quota=2,
        user_quota=1,
        used_quota=0,
        disabled=False,
    )
    await add_object_to_db(session2)
    session3 = models_ticketing.TicketingSession(
        id=uuid4(),
        event_id=event1.id,
        name="Session 3",
        quota=2,
        user_quota=1,
        used_quota=0,
        disabled=True,
    )
    await add_object_to_db(session3)

    category1 = models_ticketing.TicketingCategory(
        id=uuid4(),
        event_id=event1.id,
        name="Category 1",
        quota=2,
        user_quota=1,
        used_quota=1,
        disabled=False,
        required_mebership=None,
        price=100,
    )
    category1.sessions = [session1, session2]
    await add_object_to_db(category1)

    global student_user, student_token
    student_user = await create_user_with_groups(
        groups=[],
        account_type=AccountType.student,
    )
    student_token = create_api_access_token(student_user)


def test_get_event(client: TestClient):
    # Test with event1 (should succeed)
    response = client.get(
        f"/ticketing/events/{event1.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200

    # Test with event2 (should succeed)
    response = client.get(
        f"/ticketing/events/{event2.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200

    # Test with event_fake (not in DB, should return 404)
    response = client.get(
        f"/ticketing/events/{event_fake.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 404

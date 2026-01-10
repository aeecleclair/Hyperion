import uuid
from datetime import date

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.modules.pmf import models_pmf, schemas_pmf

# We need to import event_loop for pytest-asyncio routine defined bellow
from app.modules.pmf.types_pmf import LocationType, OfferType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

not_alumni_user: models_users.CoreUser
student_user: models_users.CoreUser
alumni_user: models_users.CoreUser

tag1_id = uuid.UUID("0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d")
tag2_id = uuid.UUID("1c8dc7bf-1ab4-421a-bbe7-7ec064fcec8d")
tag_fake_id = uuid.UUID("5e8ec7bf-4ab4-421a-bbe7-7ec064fcec8d")

offer1_id = uuid.UUID("2b7dc7bf-2ab4-421a-bbe7-7ec064fcec8d")
offer2_id = uuid.UUID("3c8dc7bf-3ab4-421a-bbe7-7ec064fcec8d")
offer3_id = uuid.UUID("4d9ec7bf-4ab4-421a-bbe7-7ec064fcec8d")
offer_fake_id = uuid.UUID("5e9ec7bf-0ab4-421a-bbe7-7ec064fcec8d")


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global not_alumni_user, student_user, alumni_user

    # We create an user in the test database
    not_alumni_user = await create_user_with_groups(
        groups=[],
        account_type=AccountType.external,
    )
    student_user = await create_user_with_groups(
        groups=[],
        account_type=AccountType.student,
    )
    alumni_user = await create_user_with_groups(
        groups=[],
        account_type=AccountType.former_student,
    )

    tag_aero = models_pmf.Tags(
        tag="Aeronautics",
        id=tag1_id,
        created_at=date(2023, 5, 1),
    )
    tag_ai = models_pmf.Tags(
        tag="Artificial Intelligence",
        id=tag2_id,
        created_at=date(2023, 5, 1),
    )
    await add_object_to_db(tag_aero)
    await add_object_to_db(tag_ai)

    # Creat 5 offers
    offer_1 = models_pmf.PmfOffer(
        id=offer1_id,
        author_id=alumni_user.id,
        company_name="AeroCorp",
        title="Aerospace Engineer Internship",
        description="Join our team to work on cutting-edge aerospace projects.",
        offer_type=OfferType.TFE,
        location="Toulouse, France",
        location_type=LocationType.On_site,
        start_date=date(2023, 6, 1),
        end_date=date(2023, 8, 31),
        created_at=date(2023, 5, 1),
        duration=92,
    )
    await add_object_to_db(offer_1)
    offer_tag = models_pmf.OfferTags(offer_id=offer_1.id, tag_id=tag_aero.id)
    await add_object_to_db(offer_tag)

    offer_2 = models_pmf.PmfOffer(
        id=offer2_id,
        author_id=alumni_user.id,
        company_name="TechAI",
        title="AI Research Internship",
        description="Work on innovative AI research projects with our expert team.",
        offer_type=OfferType.S_APP,
        location="Remote",
        location_type=LocationType.Remote,
        start_date=date(2023, 7, 1),
        end_date=date(2023, 9, 30),
        created_at=date(2023, 6, 1),
        duration=92,
    )
    await add_object_to_db(offer_2)
    offer_tag = models_pmf.OfferTags(offer_id=offer_2.id, tag_id=tag_ai.id)
    await add_object_to_db(offer_tag)

    # A 3rd offer with the two tags
    offer_3 = models_pmf.PmfOffer(
        id=offer3_id,
        author_id=alumni_user.id,
        company_name="RoboAero",
        title="Robotics and Aerospace Internship",
        description="Combine robotics and aerospace in this exciting internship.",
        offer_type=OfferType.TFE,
        location="Hybrid - Paris, France / Remote",
        location_type=LocationType.Hybrid,
        start_date=date(2023, 8, 1),
        end_date=date(2023, 10, 31),
        created_at=date(2023, 7, 1),
        duration=92,
    )
    await add_object_to_db(offer_3)
    offer_tag1 = models_pmf.OfferTags(offer_id=offer_3.id, tag_id=tag_aero.id)
    offer_tag2 = models_pmf.OfferTags(offer_id=offer_3.id, tag_id=tag_ai.id)
    await add_object_to_db(offer_tag1)
    await add_object_to_db(offer_tag2)


@pytest.mark.parametrize(
    ("offer_id", "expected_code"),
    [
        (offer1_id, 200),
        (offer2_id, 200),
        (offer3_id, 200),
        (offer_fake_id, 404),
    ],
)
def test_get_offer(offer_id: uuid.UUID, expected_code: int, client: TestClient):
    response = client.get(
        f"/offers/{offer_id}",
    )
    assert response.status_code == expected_code


@pytest.mark.parametrize(
    ("query", "expected_code", "expected_length"),
    [
        ("", 200, 3),
        (f"?tag={tag1_id}", 200, 2),
        (f"?tag={tag2_id}", 200, 2),
        (f"?tag={tag1_id}&tag={tag2_id}", 200, 1),
        (f"?tag={tag_fake_id}", 200, 0),
        (f"?offer_type={OfferType.TFE}", 200, 2),
        (f"?offer_type={OfferType.S_APP}", 200, 1),
        (f"?location_type={LocationType.On_site}", 200, 1),
        (f"?location_type={LocationType.Remote}", 200, 1),
        ("?location_type=Fake", 200, 1),
        (f"?tag={tag1_id}&offer_type={OfferType.TFE}", 200, 2),
    ],
)
def test_get_offers(
    query: uuid.UUID, expected_code: int, expected_length: int, client: TestClient
):
    response = client.get(
        f"/offers{query}",
    )
    assert response.status_code == expected_code
    assert len(response.json()) == expected_length

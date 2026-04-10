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
admin_user: models_users.CoreUser

tag1_id = uuid.UUID("0b7dc7bf-0ab4-421a-bbe7-7ec064fcec8d")
tag1: models_pmf.Tags
tag2_id = uuid.UUID("1c8dc7bf-1ab4-421a-bbe7-7ec064fcec8d")
tag2: models_pmf.Tags
tag_fake_id = uuid.UUID("5e8ec7bf-4ab4-421a-bbe7-7ec064fcec8d")

offer1_id = uuid.UUID("2b7dc7bf-2ab4-421a-bbe7-7ec064fcec8d")
offer2_id = uuid.UUID("3c8dc7bf-3ab4-421a-bbe7-7ec064fcec8d")
offer3_id = uuid.UUID("4d9ec7bf-4ab4-421a-bbe7-7ec064fcec8d")
offer_fake_id = uuid.UUID("5e9ec7bf-0ab4-421a-bbe7-7ec064fcec8d")

not_alumni_token: str
student_token: str
alumni_token: str
admin_token: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global not_alumni_user, student_user, alumni_user, admin_user

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
    admin_user = await create_user_with_groups(
        groups=[GroupType.admin],
        account_type=AccountType.former_student,
    )

    global not_alumni_token, student_token, alumni_token, admin_token
    not_alumni_token = create_api_access_token(not_alumni_user)
    student_token = create_api_access_token(student_user)
    alumni_token = create_api_access_token(alumni_user)
    admin_token = create_api_access_token(admin_user)

    global tag1, tag2
    tag1 = models_pmf.Tags(
        tag="Aeronautics",
        id=tag1_id,
        created_at=date(2023, 5, 1),
    )
    tag2 = models_pmf.Tags(
        tag="Artificial Intelligence",
        id=tag2_id,
        created_at=date(2023, 5, 1),
    )
    await add_object_to_db(tag1)
    await add_object_to_db(tag2)

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
    offer_tag = models_pmf.OfferTags(offer_id=offer_1.id, tag_id=tag1.id)
    await add_object_to_db(offer_tag)

    offer_2 = models_pmf.PmfOffer(
        id=offer2_id,
        author_id=alumni_user.id,
        company_name="TechAI",
        title="AI Research Internship",
        description="Work on innovative AI research projects with our expert team.",
        offer_type=OfferType.APP,
        location="Remote",
        location_type=LocationType.Remote,
        start_date=date(2023, 7, 1),
        end_date=date(2023, 9, 30),
        created_at=date(2023, 6, 1),
        duration=92,
    )
    await add_object_to_db(offer_2)
    offer_tag = models_pmf.OfferTags(offer_id=offer_2.id, tag_id=tag2.id)
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
    offer_tag1 = models_pmf.OfferTags(offer_id=offer_3.id, tag_id=tag1.id)
    offer_tag2 = models_pmf.OfferTags(offer_id=offer_3.id, tag_id=tag2.id)
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
        f"/pmf/offers/{offer_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == expected_code


@pytest.mark.parametrize(
    ("query", "expected_code", "expected_length"),
    [
        ("", 200, 3),
        ("?includedTags=Aeronautics", 200, 2),
        ("?includedTags=Artificial+Intelligence", 200, 2),
        ("?includedTags=Aeronautics&includedTags=Artificial+Intelligence", 200, 3),
        ("?includedTags=Fake", 200, 0),
        (f"?includedOfferTypes={OfferType.TFE.value}", 200, 2),
        (f"?includedOfferTypes={OfferType.APP.value}", 200, 1),
        (f"?includedLocationTypes={LocationType.On_site.value}", 200, 1),
        (f"?includedLocationTypes={LocationType.Remote.value}", 200, 1),
        ("?includedLocationTypes=FakeLocation", 422, 0),
        (f"?includedTags=Aeronautics&includedOfferTypes={OfferType.TFE.value}", 200, 2),
        ("?limit=2", 200, 2),
        ("?offset=1", 200, 2),
        ("?limit=2&offset=2", 200, 1),
    ],
)
def test_get_offers(
    query: uuid.UUID,
    expected_code: int,
    expected_length: int,
    client: TestClient,
):
    response = client.get(
        f"/pmf/offers/{query}",
    )
    assert response.status_code == expected_code
    if expected_code == 200:
        assert len(response.json()) == expected_length


# Tests for POST, PUT, DELETE offers
@pytest.mark.parametrize(
    ("token", "author_id", "expected_code"),
    [
        ("alumni_token", "alumni_user", 200),  # Alumni can create offer for themselves
        ("admin_token", "alumni_user", 200),  # Admin can create offer for others
        ("student_token", "student_user", 403),  # Student cannot create offers
        (
            "not_alumni_token",
            "not_alumni_user",
            403,
        ),  # External user cannot create offers
        (
            "alumni_token",
            "admin_user",
            403,
        ),  # Alumni cannot create offer for others (non-admin)
    ],
)
def test_create_offer(
    token: str,
    author_id: str,
    expected_code: int,
    client: TestClient,
):
    # Get the actual token and user id
    actual_token = globals()[token]
    actual_author_id = globals()[author_id].id

    offer_data = {
        "author_id": actual_author_id,
        "company_name": "Test Company",
        "title": "Test Position",
        "description": "This is a test offer description",
        "offer_type": OfferType.TFE.value,
        "location": "Test City",
        "location_type": LocationType.On_site.value,
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "duration": 181,
    }

    response = client.post(
        "/pmf/offer/",
        json=offer_data,
        headers={"Authorization": f"Bearer {actual_token}"},
    )
    assert response.status_code == expected_code


def test_update_offer_success(client: TestClient):
    """Test successful offer update by the author"""
    offer_update = {
        "title": "Updated Title",
        "description": "Updated description",
        "company_name": "Updated Company",
    }

    response = client.put(
        f"/pmf/offer/{offer1_id}",
        json=offer_update,
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 204


def test_update_offer_by_admin(client: TestClient):
    """Test successful offer update by admin"""
    offer_update = {
        "title": "Admin Updated Title",
    }

    response = client.put(
        f"/pmf/offer/{offer2_id}",
        json=offer_update,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_update_offer_forbidden(client: TestClient):
    """Test forbidden offer update by non-author"""
    offer_update = {
        "title": "Unauthorized Update",
    }

    response = client.put(
        f"/pmf/offer/{offer1_id}",
        json=offer_update,
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


def test_update_nonexistent_offer(client: TestClient):
    """Test update of non-existent offer"""
    offer_update = {
        "title": "Updated Title",
    }

    response = client.put(
        f"/pmf/offer/{offer_fake_id}",
        json=offer_update,
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 404


def test_delete_offer_success(client: TestClient):
    """Test successful offer deletion by the author"""
    response = client.delete(
        f"/pmf/offer/{offer3_id}",
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 204


def test_delete_offer_by_admin(client: TestClient):
    """Test successful offer deletion by admin"""
    # First create a new offer to delete
    offer_data = {
        "author_id": alumni_user.id,
        "company_name": "Delete Test Company",
        "title": "Delete Test Position",
        "description": "This offer will be deleted by admin",
        "offer_type": OfferType.APP.value,
        "location": "Delete Test City",
        "location_type": LocationType.Remote.value,
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "duration": 181,
    }

    create_response = client.post(
        "/pmf/offer/",
        json=offer_data,
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert create_response.status_code == 200
    created_offer_id = create_response.json()["id"]

    # Now delete it as admin
    response = client.delete(
        f"/pmf/offer/{created_offer_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_delete_offer_forbidden(client: TestClient):
    """Test forbidden offer deletion by non-author"""
    response = client.delete(
        f"/pmf/offer/{offer2_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


def test_delete_nonexistent_offer(client: TestClient):
    """Test deletion of non-existent offer"""
    response = client.delete(
        f"/pmf/offer/{offer_fake_id}",
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 404


# Tests for tags endpoints
def test_get_all_tags(client: TestClient):
    """Test getting all tags"""
    response = client.get("/pmf/tags/")
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) >= 2  # We have at least the 2 created tags
    assert any(tag["tag"] == "Aeronautics" for tag in tags)
    assert any(tag["tag"] == "Artificial Intelligence" for tag in tags)


def test_get_tag_by_id(client: TestClient):
    """Test getting a specific tag by ID"""
    response = client.get(f"/pmf/tag/{tag1_id}")
    assert response.status_code == 200
    tag = response.json()
    assert tag["id"] == str(tag1_id)
    assert tag["tag"] == "Aeronautics"


def test_get_nonexistent_tag(client: TestClient):
    """Test getting a non-existent tag"""
    response = client.get(f"/pmf/tag/{tag_fake_id}")
    assert response.status_code == 404


def test_create_tag_success(client: TestClient):
    """Test successful tag creation by admin"""
    tag_data = {
        "tag": "Machine Learning",
    }

    response = client.post(
        "/pmf/tag/",
        json=tag_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    created_tag = response.json()
    assert created_tag["tag"] == "Machine Learning"
    assert "id" in created_tag
    assert "created_at" in created_tag


def test_create_tag_forbidden(client: TestClient):
    """Test tag creation by non-admin user"""
    tag_data = {
        "tag": "Unauthorized Tag",
    }

    response = client.post(
        "/pmf/tag/",
        json=tag_data,
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 403


def test_create_duplicate_tag(client: TestClient):
    """Test creating a duplicate tag"""
    tag_data = {
        "tag": "Aeronautics",  # This tag already exists
    }

    response = client.post(
        "/pmf/tag/",
        json=tag_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


def test_update_tag_success(client: TestClient):
    """Test successful tag update by admin"""
    tag_update = {
        "tag": "Updated Aeronautics",
    }

    response = client.put(
        f"/pmf/tag/{tag2_id}",
        json=tag_update,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_update_tag_forbidden(client: TestClient):
    """Test tag update by non-admin user"""
    tag_update = {
        "tag": "Unauthorized Update",
    }

    response = client.put(
        f"/pmf/tag/{tag1_id}",
        json=tag_update,
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 403


def test_update_nonexistent_tag(client: TestClient):
    """Test update of non-existent tag"""
    tag_update = {
        "tag": "Updated Non-existent",
    }

    response = client.put(
        f"/pmf/tag/{tag_fake_id}",
        json=tag_update,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_delete_tag_success(client: TestClient):
    """Test successful tag deletion by admin"""
    # First create a tag to delete
    tag_data = {
        "tag": "Tag to Delete",
    }

    create_response = client.post(
        "/pmf/tag/",
        json=tag_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created_tag_id = create_response.json()["id"]

    # Now delete it
    response = client.delete(
        f"/pmf/tag/{created_tag_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_delete_tag_forbidden(client: TestClient):
    """Test tag deletion by non-admin user"""
    response = client.delete(
        f"/pmf/tag/{tag1_id}",
        headers={"Authorization": f"Bearer {alumni_token}"},
    )
    assert response.status_code == 403


def test_delete_nonexistent_tag(client: TestClient):
    """Test deletion of non-existent tag"""
    response = client.delete(
        f"/pmf/tag/{tag_fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404

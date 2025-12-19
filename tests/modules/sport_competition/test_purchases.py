from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.payment import models_payment
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import models_users
from app.modules.sport_competition import (
    cruds_sport_competition,
    models_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.permissions_sport_competition import (
    SportCompetitionPermissions,
)
from app.modules.sport_competition.types_sport_competition import (
    ProductPublicType,
    ProductSchoolType,
    SportCategory,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
    get_TestingSessionLocal,
    mocked_checkout_id,
)

school_from_lyon: models_schools.CoreSchool
school_others: models_schools.CoreSchool

active_edition: models_sport_competition.CompetitionEdition
old_edition: models_sport_competition.CompetitionEdition

admin_user: models_users.CoreUser
user_from_lyon: models_users.CoreUser
user_others: models_users.CoreUser
user_cameraman: models_users.CoreUser
user_pompom: models_users.CoreUser
user_fanfare: models_users.CoreUser
user_volunteer: models_users.CoreUser
user_multiple: models_users.CoreUser
admin_token: str
user_from_lyon_token: str
user_others_token: str
user_cameraman_token: str
user_pompom_token: str
user_fanfare_token: str
user_multiple_token: str

competition_user_admin: models_sport_competition.CompetitionUser
competition_user_from_lyon: models_sport_competition.CompetitionUser
competition_user_others: models_sport_competition.CompetitionUser
competition_user_cameraman: models_sport_competition.CompetitionUser
competition_user_pompom: models_sport_competition.CompetitionUser
competition_user_fanfare: models_sport_competition.CompetitionUser
competition_user_multiple: models_sport_competition.CompetitionUser

ecl_extension: models_sport_competition.SchoolExtension
school_from_lyon_extension: models_sport_competition.SchoolExtension
school_others_extension: models_sport_competition.SchoolExtension

product1: models_sport_competition.CompetitionProduct
product2: models_sport_competition.CompetitionProduct
product_old_edition: models_sport_competition.CompetitionProduct

school_product1_quota: models_sport_competition.SchoolProductQuota

variant_for_athlete: models_sport_competition.CompetitionProductVariant
variant_for_cameraman: models_sport_competition.CompetitionProductVariant
variant_for_pompom: models_sport_competition.CompetitionProductVariant
variant_for_fanfare: models_sport_competition.CompetitionProductVariant
variant_for_centrale: models_sport_competition.CompetitionProductVariant
variant_for_from_lyon: models_sport_competition.CompetitionProductVariant
variant_for_others: models_sport_competition.CompetitionProductVariant
variant_unique: models_sport_competition.CompetitionProductVariant
variant_disabled: models_sport_competition.CompetitionProductVariant
variant_old_edition: models_sport_competition.CompetitionProductVariant

purchase: models_sport_competition.CompetitionPurchase
purchase2: models_sport_competition.CompetitionPurchase
payment: models_sport_competition.CompetitionPayment
checkout: models_sport_competition.CompetitionCheckout


@pytest.fixture
def users():
    return {
        "admin": admin_user,
        "from_lyon": user_from_lyon,
        "others": user_others,
        "cameraman": user_cameraman,
        "pompom": user_pompom,
        "fanfare": user_fanfare,
        "multiple": user_multiple,
    }


@pytest.fixture
def user_tokens():
    return {
        "admin": admin_token,
        "from_lyon": user_from_lyon_token,
        "others": user_others_token,
        "cameraman": user_cameraman_token,
        "pompom": user_pompom_token,
        "fanfare": user_fanfare_token,
        "multiple": user_multiple_token,
    }


@pytest.fixture
def variants():
    return {
        "athlete": variant_for_athlete,
        "cameraman": variant_for_cameraman,
        "pompom": variant_for_pompom,
        "fanfare": variant_for_fanfare,
        "centrale": variant_for_centrale,
        "from_lyon": variant_for_from_lyon,
        "others": variant_for_others,
        "unique": variant_unique,
        "disabled": variant_disabled,
        "old_edition": variant_old_edition,
    }


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup():
    global admin_group
    admin_group = await create_groups_with_permissions(
        [SportCompetitionPermissions.manage_sport_competition],
        "competition_admin_group",
    )

    global school_from_lyon, school_others

    school_from_lyon = models_schools.CoreSchool(
        id=uuid4(),
        name="Lycée de Lyon",
        email_regex=".*@lyon.fr",
    )
    school_others = models_schools.CoreSchool(
        id=uuid4(),
        name="Lycée des Autres",
        email_regex=".*@autres.fr",
    )
    await add_object_to_db(school_from_lyon)
    await add_object_to_db(school_others)

    global active_edition, old_edition

    old_edition = models_sport_competition.CompetitionEdition(
        id=uuid4(),
        name="Edition 2023",
        year=2023,
        start_date=datetime(2023, 1, 1, tzinfo=UTC),
        end_date=datetime(2023, 12, 31, tzinfo=UTC),
        active=False,
        inscription_enabled=False,
    )
    await add_object_to_db(old_edition)
    active_edition = models_sport_competition.CompetitionEdition(
        id=uuid4(),
        name="Edition 2024",
        year=2024,
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(active_edition)

    global \
        admin_user, \
        user_from_lyon, \
        user_others, \
        user_cameraman, \
        user_pompom, \
        user_fanfare, \
        user_multiple
    admin_user = await create_user_with_groups(
        [admin_group.id],
        email="Admin User",
    )
    user_from_lyon = await create_user_with_groups(
        [],
        email="From Lyon User",
        school_id=school_from_lyon.id,
    )
    user_others = await create_user_with_groups(
        [],
        email="Others User",
        school_id=school_others.id,
    )
    user_cameraman = await create_user_with_groups(
        [],
        email="Cameraman User",
    )
    user_pompom = await create_user_with_groups(
        [],
        email="Pompom User",
    )
    user_fanfare = await create_user_with_groups(
        [],
        email="Fanfare User",
    )

    user_multiple = await create_user_with_groups(
        [],
        email="Multiple Roles User",
    )

    global \
        admin_token, \
        user_from_lyon_token, \
        user_others_token, \
        user_cameraman_token, \
        user_pompom_token, \
        user_fanfare_token, \
        user_multiple_token

    admin_token = create_api_access_token(admin_user)
    user_from_lyon_token = create_api_access_token(user_from_lyon)
    user_others_token = create_api_access_token(user_others)
    user_cameraman_token = create_api_access_token(user_cameraman)
    user_pompom_token = create_api_access_token(user_pompom)
    user_fanfare_token = create_api_access_token(user_fanfare)
    user_multiple_token = create_api_access_token(user_multiple)

    global \
        competition_user_admin, \
        competition_user_from_lyon, \
        competition_user_others, \
        competition_user_cameraman, \
        competition_user_pompom, \
        competition_user_fanfare, \
        competition_user_multiple

    competition_user_admin = models_sport_competition.CompetitionUser(
        user_id=admin_user.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_admin)
    competition_user_from_lyon = models_sport_competition.CompetitionUser(
        user_id=user_from_lyon.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_from_lyon)
    competition_user_others = models_sport_competition.CompetitionUser(
        user_id=user_others.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_others)
    competition_user_cameraman = models_sport_competition.CompetitionUser(
        user_id=user_cameraman.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_cameraman=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_cameraman)
    competition_user_pompom = models_sport_competition.CompetitionUser(
        user_id=user_pompom.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_pompom=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_pompom)
    competition_user_fanfare = models_sport_competition.CompetitionUser(
        user_id=user_fanfare.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_fanfare=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_fanfare)
    competition_user_multiple = models_sport_competition.CompetitionUser(
        user_id=user_multiple.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        is_cameraman=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_multiple)
    global ecl_extension, school_from_lyon_extension, school_others_extension
    ecl_extension = models_sport_competition.SchoolExtension(
        school_id=SchoolType.centrale_lyon.value,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(ecl_extension)
    school_from_lyon_extension = models_sport_competition.SchoolExtension(
        school_id=school_from_lyon.id,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_from_lyon_extension)
    school_others_extension = models_sport_competition.SchoolExtension(
        school_id=school_others.id,
        from_lyon=False,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_others_extension)

    global product1, product2, product_old_edition
    product1 = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Product 1",
        required=True,
        description="Description for Product 1",
        edition_id=active_edition.id,
    )
    await add_object_to_db(product1)
    product2 = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Product 2",
        required=False,
        description="Description for Product 2",
        edition_id=active_edition.id,
    )
    await add_object_to_db(product2)
    product_old_edition = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Old Edition Product",
        required=False,
        description="Description for Old Edition Product",
        edition_id=old_edition.id,
    )
    await add_object_to_db(product_old_edition)

    global school_product1_quota
    school_product1_quota = models_sport_competition.SchoolProductQuota(
        school_id=school_from_lyon.id,
        product_id=product1.id,
        edition_id=active_edition.id,
        quota=5,
    )
    await add_object_to_db(school_product1_quota)

    global \
        variant_for_athlete, \
        variant_for_cameraman, \
        variant_for_pompom, \
        variant_for_fanfare
    variant_for_athlete = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Athlete Variant",
        description="Variant for athletes",
        price=10000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.athlete,
    )
    await add_object_to_db(variant_for_athlete)
    variant_for_cameraman = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Cameraman Variant",
        description="Variant for cameramen",
        price=500,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.cameraman,
    )
    await add_object_to_db(variant_for_cameraman)
    variant_for_pompom = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Pompom Variant",
        description="Variant for pompom teams",
        price=300,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.pompom,
    )
    await add_object_to_db(variant_for_pompom)
    variant_for_fanfare = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Fanfare Variant",
        description="Variant for fanfare teams",
        price=400,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.fanfare,
    )
    await add_object_to_db(variant_for_fanfare)

    global variant_for_centrale, variant_for_from_lyon, variant_for_others
    variant_for_centrale = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="Centrale Variant",
        description="Variant for Centrale Lyon",
        price=1500,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_for_centrale)
    variant_for_from_lyon = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="From Lyon Variant",
        description="Variant for schools from Lyon",
        price=1200,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.from_lyon,
        public_type=None,
    )
    await add_object_to_db(variant_for_from_lyon)
    variant_for_others = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="Others Variant",
        description="Variant for other schools",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.others,
        public_type=None,
    )
    await add_object_to_db(variant_for_others)

    global variant_unique, variant_disabled, variant_old_edition

    variant_unique = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Unique Variant",
        description="Variant that can only be purchased once",
        price=2000,
        enabled=True,
        unique=True,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_unique)
    variant_disabled = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Disabled Variant",
        description="Variant that is disabled",
        price=1500,
        enabled=False,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_disabled)
    variant_old_edition = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product_old_edition.id,
        edition_id=old_edition.id,
        name="Old Edition Variant",
        description="Variant for old edition products",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_old_edition)

    global purchase, purchase2, payment, checkout
    purchase = models_sport_competition.CompetitionPurchase(
        product_variant_id=variant_for_athlete.id,
        user_id=admin_user.id,
        edition_id=active_edition.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase)
    purchase2 = models_sport_competition.CompetitionPurchase(
        product_variant_id=variant_for_centrale.id,
        user_id=admin_user.id,
        edition_id=active_edition.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase2)
    payment = models_sport_competition.CompetitionPayment(
        id=uuid4(),
        user_id=admin_user.id,
        edition_id=active_edition.id,
        total=2000,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(payment)
    base_checkout = models_payment.Checkout(
        id=uuid4(),
        module="competition",
        name="Competition Checkout",
        amount=2000,
        hello_asso_checkout_id=1,
        secret="secret",
    )
    await add_object_to_db(base_checkout)
    checkout = models_sport_competition.CompetitionCheckout(
        id=uuid4(),
        user_id=admin_user.id,
        edition_id=active_edition.id,
        checkout_id=base_checkout.id,
    )
    await add_object_to_db(checkout)


async def test_get_products(
    client: TestClient,
):
    response = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in item for item in data)
    assert all("name" in item for item in data)
    product1_data = next(
        (item for item in data if item["id"] == str(product1.id)),
        None,
    )
    assert product1_data is not None
    variant_for_athlete_data = next(
        (
            v
            for v in product1_data["variants"]
            if v["id"] == str(variant_for_athlete.id)
        ),
        None,
    )
    assert variant_for_athlete_data is not None
    assert variant_for_athlete_data["booked"] == 1
    assert variant_for_athlete_data["paid"] == 0


async def test_create_product(
    client: TestClient,
):
    new_product = schemas_sport_competition.ProductBase(
        name="New Product",
        required=False,
        description="Description for New Product",
    )

    response = client.post(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_product.model_dump(),
    )
    assert response.status_code == 201
    data = response.json()

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next((item for item in products_data if item["id"] == data["id"]), None)
    assert product is not None
    assert product["name"] == new_product.name


async def test_edit_product(
    client: TestClient,
):
    product_id = product1.id
    updated_product = {
        "name": "Updated Product 1",
        "description": "Updated description for Product 1",
    }
    response = client.patch(
        f"/competition/products/{product_id}",
        json=updated_product,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product_id)),
        None,
    )
    assert product is not None
    assert product["name"] == updated_product["name"]
    assert product["description"] == updated_product["description"]


async def test_delete_product(
    client: TestClient,
):
    product = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Product to Delete",
        required=False,
        description="Description for Product to Delete",
        edition_id=active_edition.id,
    )
    await add_object_to_db(product)
    response = client.delete(
        f"/competition/products/{product.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    assert not any(item["id"] == str(product.id) for item in products_data)


async def test_delete_product_with_variants(
    client: TestClient,
):
    response = client.delete(
        f"/competition/products/{product1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    assert any(item["id"] == str(product1.id) for item in products_data)


async def test_get_school_product_quotas(
    client: TestClient,
):
    response = client.get(
        f"/competition/schools/{school_from_lyon.id}/product-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(
        item["product_id"] == str(school_product1_quota.product_id)
        and item["quota"] == school_product1_quota.quota
        for item in data
    ), data


async def test_get_product_schools_quota(
    client: TestClient,
):
    response = client.get(
        f"/competition/products/{product1.id}/schools-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(
        item["school_id"] == str(school_product1_quota.school_id)
        and item["quota"] == school_product1_quota.quota
        for item in data
    ), data


async def test_create_school_product_quota(
    client: TestClient,
):
    new_quota = {
        "product_id": str(product1.id),
        "quota": 10,
    }
    response = client.post(
        f"/competition/schools/{school_others.id}/product-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_quota,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["school_id"] == str(school_others.id)
    assert data["product_id"] == str(new_quota["product_id"])
    assert data["quota"] == new_quota["quota"]

    quotas = client.get(
        f"/competition/schools/{school_others.id}/product-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quotas.status_code == 200
    quotas_data = quotas.json()
    assert any(
        item["product_id"] == str(new_quota["product_id"])
        and item["quota"] == new_quota["quota"]
        for item in quotas_data
    )


async def test_edit_school_product_quota(
    client: TestClient,
):
    updated_quota = {
        "quota": 15,
    }
    response = client.patch(
        f"/competition/schools/{school_from_lyon.id}/product-quotas/{product1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=updated_quota,
    )
    assert response.status_code == 204

    quotas = client.get(
        f"/competition/schools/{school_from_lyon.id}/product-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quotas.status_code == 200
    quotas_data = quotas.json()
    quota = next(
        (item for item in quotas_data if item["product_id"] == str(product1.id)),
        None,
    )
    assert quota is not None
    assert quota["quota"] == updated_quota["quota"]


async def test_delete_school_product_quota(
    client: TestClient,
):
    response = client.delete(
        f"/competition/schools/{school_from_lyon.id}/product-quotas/{product1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    quotas = client.get(
        f"/competition/schools/{school_from_lyon.id}/product-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quotas.status_code == 200
    quotas_data = quotas.json()
    assert not any(
        item["product_id"] == str(school_product1_quota.product_id)
        for item in quotas_data
    )


@pytest.mark.parametrize(
    ("token", "expected_products_variants"),
    [
        ("admin", ["athlete", "centrale", "unique"]),
        ("from_lyon", ["from_lyon"]),
        ("others", ["others"]),
        (
            "cameraman",
            ["cameraman", "centrale", "unique"],
        ),
        ("pompom", ["pompom", "centrale", "unique"]),
        ("fanfare", ["fanfare", "centrale", "unique"]),
        (
            "multiple",
            [
                "athlete",
                "centrale",
                "unique",
            ],
        ),
    ],
)
async def test_get_product_available(
    client: TestClient,
    user_tokens: dict[str, str],
    variants: dict[str, models_sport_competition.CompetitionProductVariant],
    token: str,
    expected_products_variants: list[str],
):
    response = client.get(
        "/competition/products/available",
        headers={"Authorization": f"Bearer {user_tokens[token]}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(expected_products_variants)
    assert all(
        item["id"] in [str(variants[v].id) for v in expected_products_variants]
        for item in data
    )


async def test_create_product_variants(
    client: TestClient,
):
    response = client.post(
        f"/competition/products/{product1.id}/variants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Variant",
            "description": "Description for New Variant",
            "product_id": str(product1.id),
            "price": 1500,
            "enabled": True,
            "unique": False,
            "school_type": ProductSchoolType.centrale.value,
            "public_type": ProductPublicType.athlete.value,
        },
    )
    assert response.status_code == 201
    data = response.json()

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product is not None
    assert "variants" in product
    assert any(variant["id"] == data["id"] for variant in product["variants"]), product


async def test_edit_product_variant(
    client: TestClient,
):
    variant_to_update = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Variant to Update",
        description="Description for Variant to Update",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.athlete,
    )
    await add_object_to_db(variant_to_update)
    updated_variant = {
        "name": "Updated Variant",
        "description": "Updated description for Variant",
        "price": 1200,
        "enabled": False,
        "unique": True,
        "school_type": ProductSchoolType.others.value,
        "public_type": ProductPublicType.pompom.value,
    }
    response = client.patch(
        f"/competition/products/variants/{variant_to_update.id}",
        json=updated_variant,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product is not None
    variant = next(
        (
            variant
            for variant in product["variants"]
            if variant["id"] == str(variant_to_update.id)
        ),
        None,
    )
    assert variant is not None
    assert variant["name"] == updated_variant["name"]
    assert variant["description"] == updated_variant["description"]
    assert variant["price"] == updated_variant["price"]
    assert variant["enabled"] is False
    assert variant["unique"] is True
    assert variant["school_type"] == updated_variant["school_type"]
    assert variant["public_type"] == updated_variant["public_type"]


async def test_edit_product_variant_price_with_purchases(
    client: TestClient,
):
    updated_variant = {"price": 1500}
    response = client.patch(
        f"/competition/products/variants/{variant_for_athlete.id}",
        json=updated_variant,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product is not None
    variant = next(
        (
            variant
            for variant in product["variants"]
            if variant["id"] == str(variant_for_athlete.id)
        ),
        None,
    )
    assert variant is not None
    assert variant["price"] == variant_for_athlete.price


async def test_delete_product_variant(
    client: TestClient,
):
    variant_to_delete = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Variant to Delete",
        description="Description for Variant to Delete",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.athlete,
    )
    await add_object_to_db(variant_to_delete)
    response = client.delete(
        f"/competition/products/variants/{variant_to_delete.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product is not None
    assert not any(
        variant["id"] == str(variant_to_delete.id) for variant in product["variants"]
    )


async def test_delete_product_variant_with_purchases(
    client: TestClient,
):
    response = client.delete(
        f"/competition/products/variants/{variant_for_athlete.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert products.status_code == 200
    products_data = products.json()
    product = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product is not None
    assert any(
        variant["id"] == str(variant_for_athlete.id) for variant in product["variants"]
    )


async def test_get_school_users_purchases(
    client: TestClient,
):
    response = client.get(
        f"/competition/purchases/schools/{SchoolType.centrale_lyon.value}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert admin_user.id in data
    assert isinstance(data[admin_user.id], list)
    assert len(data[admin_user.id]) == 2


async def get_user_purchases(
    client: TestClient,
):
    response = client.get(
        f"/competition/purchases/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["product_variant_id"] == str(purchase.product_variant_id)


async def test_get_user_purchases_unauthorized(
    client: TestClient,
):
    response = client.get(
        f"/competition/purchases/users/{user_others.id}",
        headers={"Authorization": f"Bearer {user_others_token}"},
    )
    assert response.status_code == 403


async def test_get_own_purchases(
    client: TestClient,
):
    response = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["product_variant_id"] == str(purchase.product_variant_id)
    assert data[1]["product_variant_id"] == str(purchase2.product_variant_id)


@pytest.mark.parametrize(
    ("token", "variant", "quantity", "expected_status"),
    [
        ("from_lyon", "from_lyon", 1, 201),
        ("others", "others", 1, 201),
        ("cameraman", "cameraman", 1, 201),
        ("pompom", "pompom", 1, 201),
        ("fanfare", "fanfare", 1, 201),
        ("multiple", "athlete", 1, 201),
        ("from_lyon", "others", 1, 403),
        ("others", "from_lyon", 1, 403),
        ("cameraman", "athlete", 1, 403),
        ("pompom", "athlete", 1, 403),
        ("fanfare", "athlete", 1, 403),
        ("multiple", "cameraman", 1, 201),
        ("multiple", "fanfare", 1, 403),
        ("admin", "disabled", 1, 403),
        ("admin", "old_edition", 1, 403),
    ],
)
async def test_create_purchase(
    client: TestClient,
    user_tokens: dict[str, str],
    variants: dict[str, models_sport_competition.CompetitionProductVariant],
    token: str,
    variant: str,
    quantity: int,
    expected_status: int,
):
    new_purchase = {
        "product_variant_id": str(variants[variant].id),
        "quantity": quantity,
    }
    response = client.post(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {user_tokens[token]}"},
        json=new_purchase,
    )
    assert response.status_code == expected_status
    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {user_tokens[token]}"},
    )
    purchases_data = purchases.json()
    if response.status_code != 201:
        assert not any(
            purchase["product_variant_id"] == str(variants[variant].id)
            for purchase in purchases_data
        )
    else:
        assert any(
            purchase["product_variant_id"] == str(variants[variant].id)
            for purchase in purchases_data
        )


async def test_delete_purchase(
    client: TestClient,
):
    purchase_to_delete = models_sport_competition.CompetitionPurchase(
        product_variant_id=variant_for_cameraman.id,
        user_id=admin_user.id,
        edition_id=active_edition.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase_to_delete)
    response = client.delete(
        f"/competition/purchases/{purchase_to_delete.product_variant_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204
    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    purchases_data = purchases.json()
    assert not any(
        purchase["product_variant_id"] == str(purchase_to_delete.product_variant_id)
        for purchase in purchases_data
    )


async def test_delete_validated_purchase(
    client: TestClient,
):
    validated_purchase = models_sport_competition.CompetitionPurchase(
        product_variant_id=variant_for_pompom.id,
        user_id=admin_user.id,
        edition_id=active_edition.id,
        quantity=1,
        validated=True,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(validated_purchase)
    response = client.delete(
        f"/competition/purchases/{validated_purchase.product_variant_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403
    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    purchases_data = purchases.json()
    assert any(
        purchase["product_variant_id"] == str(validated_purchase.product_variant_id)
        for purchase in purchases_data
    )


async def test_get_school_users_payments(
    client: TestClient,
):
    response = client.get(
        f"/competition/payments/schools/{SchoolType.centrale_lyon.value}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert admin_user.id in data
    assert isinstance(data[admin_user.id], list)
    assert len(data[admin_user.id]) == 1


async def test_get_payments(
    client: TestClient,
):
    response = client.get(
        f"/competition/users/{admin_user.id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(payment.id)


async def test_create_payment_non_validated_participant(
    client: TestClient,
):
    new_payment = {
        "total": 3000,
    }
    response = client.post(
        f"/competition/users/{user_others.id}/payments",
        headers={"Authorization": f"Bearer {user_others_token}"},
        json=new_payment,
    )
    assert response.status_code == 403


async def test_create_payment(
    client: TestClient,
):
    async with get_TestingSessionLocal()() as db:
        await cruds_sport_competition.validate_competition_user(
            admin_user.id,
            active_edition.id,
            db,
        )
        await db.commit()

    new_payment = {
        "total": 9000,
    }
    response = client.post(
        f"/competition/users/{admin_user.id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_payment,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total"] == new_payment["total"]
    assert "id" in data

    payments = client.get(
        f"/competition/users/{admin_user.id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    payments_data = payments.json()
    assert any(payment["id"] == data["id"] for payment in payments_data)

    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    purchases_data = purchases.json()
    validated_purchase = next(
        (
            each_purchase
            for each_purchase in purchases_data
            if each_purchase["product_variant_id"] == str(purchase.product_variant_id)
        ),
        None,
    )
    assert validated_purchase is not None
    assert validated_purchase["validated"] is True
    invalid_purchase = next(
        (
            each_purchase
            for each_purchase in purchases_data
            if each_purchase["product_variant_id"] == str(purchase2.product_variant_id)
        ),
        None,
    )
    assert invalid_purchase is not None
    assert invalid_purchase["validated"] is False

    products = client.get(
        "/competition/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    products_data = products.json()
    product1_data = next(
        (item for item in products_data if item["id"] == str(product1.id)),
        None,
    )
    assert product1_data is not None
    variant_for_athlete_data = next(
        (
            variant
            for variant in product1_data["variants"]
            if variant["id"] == str(variant_for_athlete.id)
        ),
        None,
    )
    assert variant_for_athlete_data is not None
    assert variant_for_athlete_data["booked"] == 2
    assert variant_for_athlete_data["paid"] == 1


async def test_delete_payment(
    client: TestClient,
):
    payment_to_delete = models_sport_competition.CompetitionPayment(
        id=uuid4(),
        user_id=admin_user.id,
        edition_id=active_edition.id,
        total=500,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(payment_to_delete)
    async with get_TestingSessionLocal()() as db:
        await cruds_sport_competition.mark_purchase_as_validated(
            admin_user.id,
            purchase2.product_variant_id,
            True,
            db,
        )
        await db.commit()

    response = client.delete(
        f"/competition/users/{admin_user.id}/payments/{payment_to_delete.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204
    payments = client.get(
        f"/competition/users/{admin_user.id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    payments_data = payments.json()
    assert not any(
        payment["id"] == str(payment_to_delete.id) for payment in payments_data
    )

    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    purchases_data = purchases.json()
    invalid_purchase = next(
        (
            each_purchase
            for each_purchase in purchases_data
            if each_purchase["product_variant_id"] == str(purchase2.product_variant_id)
        ),
        None,
    )
    assert invalid_purchase is not None
    assert invalid_purchase["validated"] is False


async def test_pay(client: TestClient):
    response = client.post(
        "/competition/pay",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["url"] == "https://some.url.fr/checkout"

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {"amount": 800, "id": 123},
            "metadata": {
                "hyperion_checkout_id": str(mocked_checkout_id),
                "secret": "checkoutsecret",
            },
        },
    )
    assert response.status_code == 204

    purchases = client.get(
        "/competition/purchases/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    purchases_data = purchases.json()
    assert all(purchase["validated"] is True for purchase in purchases_data)

    payments = client.get(
        f"/competition/users/{admin_user.id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    payments_data = payments.json()

    assert any(payment["total"] == 800 for payment in payments_data)


async def test_data_exporter(
    client: TestClient,
):
    response = client.get(
        "/competition/users/data-export?included_fields=purchases&included_fields=payments&included_fields=participants",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

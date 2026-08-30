import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups import models_groups
from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.sdec_facturation import (
    cruds_sdec_facturation,
    models_sdec_facturation,
    schemas_sdec_facturation,
)
from app.modules.sdec_facturation.types_sdec_facturation import (
    AssociationStructureType,
    AssociationType,
    IndividualCategoryType,
    ProductCategoryType,
    RoleType,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
    get_TestingSessionLocal,
)

sdec_facturation_admin: models_users.CoreUser
sdec_facturation_user: models_users.CoreUser
token_admin: str
token_user: str

member1: models_sdec_facturation.Member
member2: models_sdec_facturation.Member

mandate: models_sdec_facturation.Mandate

association1: models_sdec_facturation.Association
association2: models_sdec_facturation.Association
association3: models_sdec_facturation.Association

product1: models_sdec_facturation.Product
product2: models_sdec_facturation.Product
product3: models_sdec_facturation.Product
product4: models_sdec_facturation.Product

productPrice1: models_sdec_facturation.ProductPrice
productPrice2: models_sdec_facturation.ProductPrice
productPrice3: models_sdec_facturation.ProductPrice
productPrice4: models_sdec_facturation.ProductPrice
productPrice5: models_sdec_facturation.ProductPrice

order1: models_sdec_facturation.Order
order2: models_sdec_facturation.Order

factureAssociation1: models_sdec_facturation.FactureAssociation

FactureIndividual1: models_sdec_facturation.FactureIndividual


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global sdec_facturation_admin, token_admin
    sdec_facturation_admin = await create_user_with_groups(
        [GroupType.sdec_facturation_admin],
    )
    token_admin = create_api_access_token(sdec_facturation_admin)

    global sdec_facturation_user, token_user
    sdec_facturation_user = await create_user_with_groups(
        [],
    )
    token_user = create_api_access_token(sdec_facturation_user)

    global member1, member2
    member1 = models_sdec_facturation.Member(
        id=uuid.uuid4(),
        name="Member 1",
        mandate=2023,
        role=RoleType.prez,
        modified_date=datetime(2023, 1, 1, tzinfo=UTC),
        visible=True,
    )
    await add_object_to_db(member1)
    member2 = models_sdec_facturation.Member(
        id=uuid.uuid4(),
        name="Member 2",
        mandate=2023,
        role=RoleType.trez,
        modified_date=datetime(2023, 2, 1, tzinfo=UTC),
        visible=True,
    )
    await add_object_to_db(member2)

    global mandate
    mandate = models_sdec_facturation.Mandate(
        year=2023,
        name="Mandate 2023",
    )
    await add_object_to_db(mandate)

    global association1, association2, association3
    association1 = models_sdec_facturation.Association(
        id=uuid.uuid4(),
        name="Association 1",
        type=AssociationType.aeecl,
        structure=AssociationStructureType.asso,
        modified_date=datetime(2023, 1, 15, tzinfo=UTC),
        visible=True,
    )
    await add_object_to_db(association1)
    association2 = models_sdec_facturation.Association(
        id=uuid.uuid4(),
        name="Association 2",
        type=AssociationType.useecl,
        structure=AssociationStructureType.club,
        modified_date=datetime(2023, 2, 15, tzinfo=UTC),
        visible=True,
    )
    await add_object_to_db(association2)
    association3 = models_sdec_facturation.Association(
        id=uuid.uuid4(),
        name="Association 3",
        type=AssociationType.independant,
        structure=AssociationStructureType.section,
        modified_date=datetime(2023, 3, 15, tzinfo=UTC),
        visible=True,
    )
    await add_object_to_db(association3)

    global product1, product2, product3, product4
    product1 = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code="P001",
        name="Product 1",
        category=ProductCategoryType.impression,
        creation_date=datetime(2023, 1, 10, tzinfo=UTC),
        for_sale=True,
    )
    await add_object_to_db(product1)
    product2 = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code="P002",
        name="Product 2",
        category=ProductCategoryType.papier_a4,
        creation_date=datetime(2023, 1, 10, tzinfo=UTC),
        for_sale=True,
    )
    await add_object_to_db(product2)
    product3 = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code="P003",
        name="Product 3",
        category=ProductCategoryType.enveloppe,
        creation_date=datetime(2023, 1, 10, tzinfo=UTC),
        for_sale=True,
    )
    await add_object_to_db(product3)
    product4 = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code="P004",
        name="Product 4",
        category=ProductCategoryType.ticket,
        creation_date=datetime(2023, 1, 10, tzinfo=UTC),
        for_sale=True,
    )
    await add_object_to_db(product4)

    global productPrice1, productPrice2, productPrice3, productPrice4, productPrice5
    productPrice1 = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product1.id,
        individual_price=1.0,
        association_price=0.8,
        ae_price=0.5,
        effective_date=datetime(2023, 1, 15, tzinfo=UTC),
    )
    await add_object_to_db(productPrice1)
    productPrice2 = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product2.id,
        individual_price=2.0,
        association_price=1.5,
        ae_price=1.0,
        effective_date=datetime(2023, 1, 15, tzinfo=UTC),
    )
    await add_object_to_db(productPrice2)
    productPrice3 = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product3.id,
        individual_price=3.0,
        association_price=2.5,
        ae_price=2.0,
        effective_date=datetime(2023, 1, 15, tzinfo=UTC),
    )
    await add_object_to_db(productPrice3)
    productPrice4 = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product4.id,
        individual_price=4.0,
        association_price=3.5,
        ae_price=3.0,
        effective_date=datetime.now(tz=UTC),
    )
    await add_object_to_db(productPrice4)
    productPrice5 = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product1.id,
        individual_price=1.2,
        association_price=0.9,
        ae_price=0.6,
        effective_date=datetime(2023, 2, 15, tzinfo=UTC),
    )
    await add_object_to_db(productPrice5)

    global order1, order2
    order1 = models_sdec_facturation.Order(
        id=uuid.uuid4(),
        association_id=association1.id,
        member_id=member1.id,
        order="Product 1:10,Product 2:5",
        creation_date=datetime(2023, 3, 1, tzinfo=UTC),
        valid=True,
    )
    await add_object_to_db(order1)
    order2 = models_sdec_facturation.Order(
        id=uuid.uuid4(),
        association_id=association2.id,
        member_id=member2.id,
        order="Product 3:7,Product 4:3",
        creation_date=datetime(2023, 3, 5, tzinfo=UTC),
        valid=True,
    )
    await add_object_to_db(order2)

    global factureAssociation1
    factureAssociation1 = models_sdec_facturation.FactureAssociation(
        id=uuid.uuid4(),
        facture_number="FA2023001",
        member_id=member1.id,
        association_id=association1.id,
        start_date=datetime(2023, 1, 1, tzinfo=UTC),
        end_date=datetime(2023, 12, 31, tzinfo=UTC),
        price=150.0,
        facture_date=datetime(2023, 3, 10, tzinfo=UTC),
        paid=False,
        valid=True,
        payment_date=None,
    )
    await add_object_to_db(factureAssociation1)

    global FactureIndividual1
    FactureIndividual1 = models_sdec_facturation.FactureIndividual(
        id=uuid.uuid4(),
        facture_number="FI2023001",
        member_id=member2.id,
        individual_order="Product 1:2,Product 4:1",
        individual_category=IndividualCategoryType.pe,
        price=6.4,
        facture_date=datetime(2023, 3, 12, tzinfo=UTC),
        firstname="John",
        lastname="Doe",
        adresse="123 Main St",
        postal_code="69000",
        city="Lyon",
        country="France",
        paid=False,
        valid=True,
        payment_date=None,
    )
    await add_object_to_db(FactureIndividual1)


# ---------------------------------------------------------------------------- #
#                                  Get tests                                   #
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
#                                     Member                                   #
# ---------------------------------------------------------------------------- #


def test_get_all_members(client: TestClient):
    """Test retrieving all members."""
    response = client.get(
        "/sdec_facturation/member/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_member(client: TestClient):
    """Test creating a new member."""
    new_member_data = {
        "name": "Member 3",
        "mandate": 2023,
        "role": "com",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/member/",
        json=new_member_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    member = response.json()
    assert member["name"] == "Member 3"
    assert member["mandate"] == 2023
    assert member["role"] == "com"
    assert member["visible"] is True
    modified_date = datetime.fromisoformat(member["modified_date"]).date()
    current_date = datetime.now(tz=UTC).date()
    assert modified_date == current_date
    assert isinstance(member["id"], str)

    repeated_member_data = {
        "name": "Member 2",
        "mandate": 2023,
        "role": "com",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/member/",
        json=repeated_member_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate member name


def test_create_member_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new member."""
    new_member_data = {
        "name": "Member 4",
        "mandate": 2023,
        "role": "profs",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/member/",
        json=new_member_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_member(client: TestClient):
    """Test updating an existing member."""
    update_data = {
        "name": "Updated Member 1",
        "role": "trez_ext",
        "visible": False,
    }
    response = client.put(
        f"/sdec_facturation/member/{member1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    repeated_name_data = {
        "name": "Member 2",
        "role": "sg",
        "visible": True,
    }
    response = client.put(
        f"/sdec_facturation/member/{member1.id}",
        json=repeated_name_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )


def test_update_member_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update a member."""
    update_data = {
        "name": "Malicious Update",
        "role": "sg",
        "visible": True,
    }
    response = client.put(
        f"/sdec_facturation/member/{member1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_member(client: TestClient):
    """Test deleting a member."""
    response = client.delete(
        f"/sdec_facturation/member/{member2.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    # Verify deletion
    get_response = client.get(
        f"/sdec_facturation/member/{member2.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert get_response.status_code == 404


def test_delete_member_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete a member."""
    response = client.delete(
        f"/sdec_facturation/member/{member1.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                     Mandate                                  #
# ---------------------------------------------------------------------------- #
def test_get_all_mandates(client: TestClient):
    """Test retrieving all mandates."""
    response = client.get(
        "/sdec_facturation/mandate/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_mandate(client: TestClient):
    """Test creating a new mandate."""
    new_mandate_data = {
        "year": 2024,
        "name": "Mandate 2024",
    }
    response = client.post(
        "/sdec_facturation/mandate/",
        json=new_mandate_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    mandate = response.json()
    assert mandate["year"] == 2024
    assert mandate["name"] == "Mandate 2024"

    repeated_mandate_data = {
        "year": 2023,
        "name": "Duplicate Mandate 2023",
    }
    response = client.post(
        "/sdec_facturation/mandate/",
        json=repeated_mandate_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate mandate year


def test_create_mandate_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new mandate."""
    new_mandate_data = {
        "year": 2025,
        "name": "Mandate 2025",
    }
    response = client.post(
        "/sdec_facturation/mandate/",
        json=new_mandate_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_mandate(client: TestClient):
    """Test updating an existing mandate."""
    update_data = {
        "name": "Updated Mandate 2023",
    }
    response = client.put(
        f"/sdec_facturation/mandate/{mandate.year}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_mandate_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update a mandate."""
    update_data = {
        "name": "Malicious Mandate Update",
    }
    response = client.put(
        f"/sdec_facturation/mandate/{mandate.year}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_mandate(client: TestClient):
    """Test deleting a mandate."""
    response = client.delete(
        f"/sdec_facturation/mandate/{mandate.year}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    # Verify deletion
    get_response = client.get(
        f"/sdec_facturation/mandate/{mandate.year}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert get_response.status_code == 404


def test_delete_mandate_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete a mandate."""
    response = client.delete(
        f"/sdec_facturation/mandate/{mandate.year}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
def test_get_all_associations(client: TestClient):
    """Test retrieving all associations."""
    response = client.get(
        "/sdec_facturation/association/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_create_association(client: TestClient):
    """Test creating a new association."""
    new_association_data = {
        "name": "Association 4",
        "type": "aeecl",
        "structure": "club",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/association/",
        json=new_association_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    association = response.json()
    assert association["name"] == "Association 4"
    assert association["type"] == "aeecl"
    assert association["structure"] == "club"
    assert association["visible"] is True
    modified_date = datetime.fromisoformat(association["modified_date"]).date()
    current_date = datetime.now(tz=UTC).date()
    assert modified_date == current_date
    assert isinstance(association["id"], str)

    repeated_association_data = {
        "name": "Association 1",
        "type": "useecl",
        "structure": "asso",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/association/",
        json=repeated_association_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate association name


def test_create_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new association."""
    new_association_data = {
        "name": "Association 5",
        "type": "useecl",
        "structure": "section",
        "visible": True,
    }
    response = client.post(
        "/sdec_facturation/association/",
        json=new_association_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_association(client: TestClient):
    """Test updating an existing association."""
    update_data = {
        "name": "Updated Association 1",
        "structure": "section",
        "visible": False,
    }
    response = client.put(
        f"/sdec_facturation/association/{association1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    repeated_name_data = {
        "name": "Association 2",
        "structure": "club",
        "visible": True,
    }
    response = client.put(
        f"/sdec_facturation/association/{association1.id}",
        json=repeated_name_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate association name


def test_update_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update an association."""
    update_data = {
        "name": "Malicious Association Update",
        "structure": "asso",
        "visible": True,
    }
    response = client.put(
        f"/sdec_facturation/association/{association1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_association(client: TestClient):
    """Test deleting an association."""
    response = client.delete(
        f"/sdec_facturation/association/{association2.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    # Verify deletion
    get_response = client.get(
        f"/sdec_facturation/association/{association2.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert get_response.status_code == 404


def test_delete_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete an association."""
    response = client.delete(
        f"/sdec_facturation/association/{association1.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                     Product                                 #
# ---------------------------------------------------------------------------- #
def test_get_all_products(client: TestClient):
    """Test retrieving all products."""
    response = client.get(
        "/sdec_facturation/product/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_create_product(client: TestClient):
    """Test creating a new product."""
    new_product_data = {
        "code": "P005",
        "name": "Product 5",
        "category": "divers",
        "for_sale": True,
        "individual_price": 5.0,
        "association_price": 4.0,
        "ae_price": 3.0,
    }
    response = client.post(
        "/sdec_facturation/product/",
        json=new_product_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    product = response.json()
    assert product["code"] == "P005"
    assert product["name"] == "Product 5"
    assert product["category"] == "divers"
    assert product["for_sale"] is True
    assert product["individual_price"] == 5.0
    assert product["association_price"] == 4.0
    assert product["ae_price"] == 3.0
    creation_date = datetime.fromisoformat(product["creation_date"]).date()
    current_date = datetime.now(tz=UTC).date()
    assert creation_date == current_date
    effective_date = datetime.fromisoformat(product["effective_date"]).date()
    current_date = datetime.now(tz=UTC).date()
    assert effective_date == current_date
    assert isinstance(product["id"], str)

    repeated_product_data = {
        "code": "P001",
        "name": "Duplicate Product 1",
        "category": "impression",
        "for_sale": True,
        "individual_price": 1.0,
        "association_price": 0.8,
        "ae_price": 0.5,
    }
    response = client.post(
        "/sdec_facturation/product/",
        json=repeated_product_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate product code


def test_create_product_lack_price(client: TestClient):
    """Test creating a new product without price fields."""
    lack_price_data = {
        "code": "P006",
        "name": "Product 6",
        "category": "divers",
        "for_sale": True,
    }
    response = client.post(
        "/sdec_facturation/product/",
        json=lack_price_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to missing price fields


def test_create_product_invalid_price(client: TestClient):
    """Test creating a new product with invalid price values."""
    invalid_price_data = {
        "code": "P007",
        "name": "Product 7",
        "category": "divers",
        "for_sale": True,
        "individual_price": -1.0,  # Invalid negative price
        "association_price": 2.0,
        "ae_price": 1.0,
    }
    response = client.post(
        "/sdec_facturation/product/",
        json=invalid_price_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid price value


def test_create_product_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new product."""
    new_product_data = {
        "code": "P008",
        "name": "Product 8",
        "category": "divers",
        "for_sale": True,
        "individual_price": 8.0,
        "association_price": 6.0,
        "ae_price": 4.0,
    }
    response = client.post(
        "/sdec_facturation/product/",
        json=new_product_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_product(client: TestClient):
    """Test updating an existing product."""
    update_data = {
        "name": "Updated Product 1",
        "category": "tshirt_flocage",
        "for_sale": False,
    }
    response = client.put(
        f"/sdec_facturation/product/{product1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    repeated_name_data = {
        "name": "Product 2",
        "category": "impression",
        "for_sale": True,
    }
    response = client.put(
        f"/sdec_facturation/product/{product1.id}",
        json=repeated_name_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to duplicate product name


def test_update_product_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update a product."""
    update_data = {
        "name": "Malicious Product Update",
        "category": "divers",
        "for_sale": True,
    }
    response = client.put(
        f"/sdec_facturation/product/{product1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_price_not_today(client: TestClient):
    """Test updating the price of an existing product."""
    update_price_data = {
        "individual_price": 2.15,
        "association_price": 1.51,
        "ae_price": 1.12,
    }
    response = client.put(
        f"/sdec_facturation/product/price/{product2.id}",
        json=update_price_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_price_today(client: TestClient):
    """Test updating the price of an existing product with today's date."""
    update_price_data = {
        "individual_price": 2.50,
        "association_price": 1.75,
        "ae_price": 1.25,
    }
    response = client.put(
        f"/sdec_facturation/product/price/{product4.id}",
        json=update_price_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_price_invalid(client: TestClient):
    """Test updating a product's price with invalid values."""
    invalid_price_data = {
        "individual_price": -3.0,  # Invalid negative price
        "association_price": 2.0,
        "ae_price": 1.0,
    }
    response = client.put(
        f"/sdec_facturation/product/price/{product2.id}",
        json=invalid_price_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid price value


def test_update_price_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update a product's price."""
    update_price_data = {
        "individual_price": 3.0,
        "association_price": 2.0,
        "ae_price": 1.0,
    }
    response = client.put(
        f"/sdec_facturation/product/price/{product2.id}",
        json=update_price_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_product(client: TestClient):
    """Test deleting a product."""
    response = client.delete(
        f"/sdec_facturation/product/{product3.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_product_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete a product."""
    response = client.delete(
        f"/sdec_facturation/product/{product1.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                                   Order                                      #
# ---------------------------------------------------------------------------- #


def test_get_all_orders(client: TestClient):
    """Test retrieving all orders."""
    response = client.get(
        "/sdec_facturation/order/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_order(client: TestClient):
    """Test creating a new order."""
    new_order_data = {
        "association_id": str(association3.id),
        "member_id": str(member1.id),
        "order": "Product 2:4,Product 4:2",
        "valid": True,
    }
    response = client.post(
        "/sdec_facturation/order/",
        json=new_order_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    order = response.json()
    assert order["association_id"] == str(association3.id)
    assert order["member_id"] == str(member1.id)
    assert order["order"] == "Product 2:4,Product 4:2"
    assert order["valid"] is True
    creation_date = datetime.fromisoformat(order["creation_date"]).date()
    current_date = datetime.now(tz=UTC).date()
    assert creation_date == current_date
    assert isinstance(order["id"], str)


def test_create_order_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new order."""
    new_order_data = {
        "association_id": str(association3.id),
        "member_id": str(member1.id),
        "order": "Product 2:4,Product 4:2",
        "valid": True,
    }
    response = client.post(
        "/sdec_facturation/order/",
        json=new_order_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_order(client: TestClient):
    """Test updating an existing order."""
    update_data = {
        "order": "Product 1:5,Product 3:3",
    }
    response = client.put(
        f"/sdec_facturation/order/{order1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_order_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update an order."""
    update_data = {
        "order": "Product 2:6,Product 4:4",
    }
    response = client.put(
        f"/sdec_facturation/order/{order1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_order(client: TestClient):
    """Test deleting an order."""
    response = client.delete(
        f"/sdec_facturation/order/{order2.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------- #
#                              Facture Association                             #
# ---------------------------------------------------------------------------- #


def test_get_all_facture_associations(client: TestClient):
    """Test retrieving all association invoices."""
    response = client.get(
        "/sdec_facturation/facture_association/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_facture_association(client: TestClient):
    """Test creating a new association invoice."""
    new_facture_data = {
        "facture_number": "FA2023002",
        "member_id": str(member2.id),
        "association_id": str(association2.id),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "price": 200.0,
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_association/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    facture_association = response.json()
    assert facture_association["facture_number"] == "FA2023002"
    assert facture_association["member_id"] == str(member2.id)
    assert facture_association["association_id"] == str(association2.id)
    assert facture_association["start_date"] == "2023-01-01T00:00:00+00:00"
    assert facture_association["end_date"] == "2023-12-31T00:00:00+00:00"
    assert facture_association["price"] == 200.0
    assert facture_association["paid"] is False
    assert facture_association["valid"] is True
    facture_date = datetime.fromisoformat(facture_association["facture_date"]).date()
    assert facture_date == datetime.now(tz=UTC).date()
    assert isinstance(facture_association["id"], str)


def test_create_facture_association_invalid_price(client: TestClient):
    """Test creating a new association invoice with invalid price."""
    new_facture_data = {
        "facture_number": "FA2023003",
        "member_id": str(member2.id),
        "association_id": str(association2.id),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "price": -100.0,  # Invalid negative price
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_association/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid price value


def test_create_facture_association_invalid_dates(client: TestClient):
    """Test creating a new association invoice with invalid dates."""
    new_facture_data = {
        "facture_number": "FA2023004",
        "member_id": str(member2.id),
        "association_id": str(association2.id),
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",  # End date before start date
        "price": 150.0,
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_association/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid date range


def test_create_facture_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new association invoice."""
    new_facture_data = {
        "facture_number": "FA2023005",
        "member_id": str(member2.id),
        "association_id": str(association2.id),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "price": 180.0,
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_association/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_facture_association(client: TestClient):
    """Test updating an existing association invoice."""
    update_data = {
        "paid": True,
    }
    response = client.put(
        f"/sdec_facturation/facture_association/{factureAssociation1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_facture_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update an association invoice."""
    update_data = {
        "paid": True,
    }
    response = client.put(
        f"/sdec_facturation/facture_association/{factureAssociation1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_facture_association(client: TestClient):
    """Test deleting an association invoice."""
    response = client.delete(
        f"/sdec_facturation/facture_association/{factureAssociation1.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_facture_association_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete an association invoice."""
    response = client.delete(
        f"/sdec_facturation/facture_association/{factureAssociation1.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------- #
#                               Facture Individual                             #
# ---------------------------------------------------------------------------- #
def test_get_all_facture_individuals(client: TestClient):
    """Test retrieving all individual invoices."""
    response = client.get(
        "/sdec_facturation/facture_individual/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_facture_individual(client: TestClient):
    """Test creating a new individual invoice."""
    new_facture_data = {
        "facture_number": "FI2023002",
        "member_id": str(member1.id),
        "individual_order": "Product 2:3,Product 3:2",
        "individual_category": "profs",
        "price": 10.5,
        "firstname": "Alice",
        "lastname": "Smith",
        "adresse": "456 Elm St",
        "postal_code": "75001",
        "city": "Paris",
        "country": "France",
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_individual/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    facture_individual = response.json()
    assert facture_individual["facture_number"] == "FI2023002"
    assert facture_individual["member_id"] == str(member1.id)
    assert facture_individual["individual_order"] == "Product 2:3,Product 3:2"
    assert facture_individual["individual_category"] == "profs"
    assert facture_individual["price"] == 10.5
    assert facture_individual["firstname"] == "Alice"
    assert facture_individual["lastname"] == "Smith"
    assert facture_individual["adresse"] == "456 Elm St"
    assert facture_individual["postal_code"] == "75001"
    assert facture_individual["city"] == "Paris"
    assert facture_individual["country"] == "France"
    assert facture_individual["paid"] is False
    assert facture_individual["valid"] is True
    facture_date = datetime.fromisoformat(facture_individual["facture_date"]).date()
    assert facture_date == datetime.now(tz=UTC).date()
    assert isinstance(facture_individual["id"], str)


def test_create_facture_individual_invalid_price(client: TestClient):
    """Test creating a new individual invoice with invalid price."""
    new_facture_data = {
        "facture_number": "FI2023003",
        "member_id": str(member1.id),
        "individual_order": "Product 2:3,Product 3:2",
        "individual_category": "profs",
        "price": -5.0,  # Invalid negative price
        "firstname": "Bob",
        "lastname": "Brown",
        "adresse": "789 Oak St",
        "postal_code": "13001",
        "city": "Marseille",
        "country": "France",
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_individual/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid price value


def test_create_facture_individual_invalid_name(client: TestClient):
    """Test creating a new individual invoice with invalid name."""
    new_facture_data = {
        "facture_number": "FI2023004",
        "member_id": str(member1.id),
        "individual_order": "Product 2:3,Product 3:2",
        "individual_category": "profs",
        "price": 15.0,
        "firstname": "",  # Invalid empty firstname
        "lastname": "Green",
        "adresse": "101 Pine St",
        "postal_code": "31000",
        "city": "Toulouse",
        "country": "France",
        "paid": False,
        "valid": True,
        "payment_date": None,
    }
    response = client.post(
        "/sdec_facturation/facture_individual/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400  # Bad Request due to invalid firstname


def test_create_facture_individual_as_lambda(client: TestClient):
    """Test that a non-admin user cannot create a new individual invoice."""
    new_facture_data = {
        "facture_number": "FI2023005",
        "member_id": str(member1.id),
        "individual_order": "Product 2:3,Product 3:2",
        "individual_category": "profs",
        "price": 12.0,
        "firstname": "Charlie",
        "lastname": "Davis",
        "adresse": "202 Birch St",
        "postal_code": "44000",
        "city": "Nantes",
        "country": "France",
        "paid": False,
    }
    response = client.post(
        "/sdec_facturation/facture_individual/",
        json=new_facture_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_facture_individual(client: TestClient):
    """Test updating an existing individual invoice."""
    update_data = {
        "paid": True,
    }
    response = client.put(
        f"/sdec_facturation/facture_individual/{FactureIndividual1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_facture_individual_as_lambda(client: TestClient):
    """Test that a non-admin user cannot update an individual invoice."""
    update_data = {
        "paid": True,
    }
    response = client.put(
        f"/sdec_facturation/facture_individual/{FactureIndividual1.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_delete_facture_individual(client: TestClient):
    """Test deleting an individual invoice."""
    response = client.delete(
        f"/sdec_facturation/facture_individual/{FactureIndividual1.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_delete_facture_individual_as_lambda(client: TestClient):
    """Test that a non-admin user cannot delete an individual invoice."""
    response = client.delete(
        f"/sdec_facturation/facture_individual/{FactureIndividual1.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

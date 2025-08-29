import uuid
from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.groups.groups_type import GroupType
from app.core.memberships import models_memberships
from app.core.users import models_users
from app.modules.cdr import models_cdr
from app.modules.cdr.coredata_cdr import CdrYear
from app.modules.cdr.types_cdr import (
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
)
from tests.commons import (
    add_coredata_to_db,
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

year = datetime.now(UTC).year

cdr_admin: models_users.CoreUser
cdr_bde: models_users.CoreUser
cdr_user: models_users.CoreUser

token_admin: str
token_bde: str
token_user: str

seller: models_cdr.Seller
online_seller: models_cdr.Seller
empty_seller: models_cdr.Seller

product: models_cdr.CdrProduct
online_product: models_cdr.CdrProduct
empty_product: models_cdr.CdrProduct
usable_product: models_cdr.CdrProduct
ticket_product: models_cdr.CdrProduct

document: models_cdr.Document
unused_document: models_cdr.Document
other_document: models_cdr.Document

document_constraint: models_cdr.DocumentConstraint
product_constraint: models_cdr.ProductConstraint

variant: models_cdr.ProductVariant
empty_variant: models_cdr.ProductVariant
ticket_variant: models_cdr.ProductVariant

curriculum: models_cdr.Curriculum
unused_curriculum: models_cdr.Curriculum

cdr_user_with_curriculum_with_non_validated_purchase: models_users.CoreUser

purchase: models_cdr.Purchase

signature: models_cdr.Signature
signature_admin: models_cdr.Signature

payment: models_cdr.Payment


association_membership: models_memberships.CoreAssociationMembership
user_membership: models_memberships.CoreAssociationUserMembership

ticket: models_cdr.Ticket
ticket_generator: models_cdr.TicketGenerator


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    await add_coredata_to_db(CdrYear(year=year))

    global cdr_admin
    cdr_admin = await create_user_with_groups(
        [GroupType.admin_cdr],
        email="cdr_admin@etu.ec-lyon.fr",
    )

    global token_admin
    token_admin = create_api_access_token(cdr_admin)

    global cdr_bde
    cdr_bde = await create_user_with_groups(
        [GroupType.BDE],
    )

    global token_bde
    token_bde = create_api_access_token(cdr_bde)

    global cdr_user
    cdr_user = await create_user_with_groups(
        [],
    )

    global token_user
    token_user = create_api_access_token(cdr_user)

    global seller
    seller = models_cdr.Seller(
        id=uuid.uuid4(),
        name="BDE",
        group_id=str(GroupType.BDE.value),
        order=5,
    )
    await add_object_to_db(seller)

    global online_seller
    online_seller = models_cdr.Seller(
        id=uuid.uuid4(),
        name="CAA",
        group_id=str(GroupType.CAA.value),
        order=12,
    )
    await add_object_to_db(online_seller)

    global empty_seller
    empty_seller = models_cdr.Seller(
        id=uuid.uuid4(),
        name="Seller Vide",
        group_id=str(GroupType.cinema.value),
        order=99,
    )
    await add_object_to_db(empty_seller)

    global product
    product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit",
        name_en="Product",
        description_fr="Un Produit",
        description_en="A Product",
        available_online=False,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(product)

    global online_product
    online_product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=online_seller.id,
        name_fr="Produit en ligne",
        name_en="Online Product",
        description_fr="Un Produit disponible en ligne",
        description_en="An online available Product",
        available_online=True,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(online_product)

    global empty_product
    empty_product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit sans variante",
        name_en="Unused product",
        available_online=False,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(empty_product)

    global usable_product
    usable_product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit utilisable",
        name_en="Usable product",
        available_online=False,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(usable_product)

    global document
    document = models_cdr.Document(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name="Document à signer",
    )
    await add_object_to_db(document)

    global unused_document
    unused_document = models_cdr.Document(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name="Document non utilisé",
    )
    await add_object_to_db(unused_document)

    global other_document
    other_document = models_cdr.Document(
        id=uuid.uuid4(),
        seller_id=online_seller.id,
        name="Document non utilisé",
    )
    await add_object_to_db(other_document)

    global document_constraint
    document_constraint = models_cdr.DocumentConstraint(
        product_id=product.id,
        document_id=document.id,
    )
    await add_object_to_db(document_constraint)

    global product_constraint
    product_constraint = models_cdr.ProductConstraint(
        product_id=product.id,
        product_constraint_id=online_product.id,
    )
    await add_object_to_db(product_constraint)

    global variant
    variant = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(variant)

    global empty_variant
    empty_variant = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante vide",
        name_en="Empty variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(empty_variant)

    global curriculum
    curriculum = models_cdr.Curriculum(
        id=uuid.uuid4(),
        name="Ingénieur généraliste",
    )
    await add_object_to_db(curriculum)

    global unused_curriculum
    unused_curriculum = models_cdr.Curriculum(
        id=uuid.uuid4(),
        name="Ingénieur généraliste inutile",
    )
    await add_object_to_db(unused_curriculum)

    cdr_user_with_curriculum_without_purchase = await create_user_with_groups(
        [],
    )
    curriculum_membership = models_cdr.CurriculumMembership(
        user_id=cdr_user_with_curriculum_without_purchase.id,
        curriculum_id=curriculum.id,
    )
    await add_object_to_db(curriculum_membership)

    global cdr_user_with_curriculum_with_non_validated_purchase
    cdr_user_with_curriculum_with_non_validated_purchase = (
        await create_user_with_groups(
            [],
        )
    )
    curriculum_membership_for_user_with_curriculum_with_non_validated_purchase = (
        models_cdr.CurriculumMembership(
            user_id=cdr_user_with_curriculum_with_non_validated_purchase.id,
            curriculum_id=curriculum.id,
        )
    )
    await add_object_to_db(
        curriculum_membership_for_user_with_curriculum_with_non_validated_purchase,
    )
    purchase_for_user_with_curriculum_with_non_validated_purchase = models_cdr.Purchase(
        user_id=cdr_user_with_curriculum_with_non_validated_purchase.id,
        product_variant_id=variant.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(
        purchase_for_user_with_curriculum_with_non_validated_purchase,
    )

    global purchase
    purchase = models_cdr.Purchase(
        user_id=cdr_user.id,
        product_variant_id=variant.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase)

    global signature
    signature = models_cdr.Signature(
        user_id=cdr_user.id,
        document_id=document.id,
        signature_type=DocumentSignatureType.numeric,
        numeric_signature_id="somedocumensoid",
    )
    await add_object_to_db(signature)

    global payment
    payment = models_cdr.Payment(
        id=uuid.uuid4(),
        user_id=cdr_user.id,
        total=5000,
        payment_type=PaymentType.cash,
        year=year,
    )
    await add_object_to_db(payment)

    global association_membership
    association_membership = models_memberships.CoreAssociationMembership(
        id=uuid.uuid4(),
        name="AEECL",
        manager_group_id=GroupType.BDE,
    )
    await add_object_to_db(association_membership)

    global user_membership
    user_membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=cdr_user.id,
        association_membership_id=association_membership.id,
        start_date=date(2022, 9, 1),
        end_date=date(2026, 9, 1),
    )
    await add_object_to_db(user_membership)

    global ticket_product
    ticket_product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit a ticket",
        name_en="Usable product",
        available_online=False,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(ticket_product)

    global ticket_variant
    ticket_variant = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=ticket_product.id,
        name_fr="variante a ticket",
        name_en="Empty variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(ticket_variant)

    global ticket_generator
    ticket_generator = models_cdr.TicketGenerator(
        id=uuid.uuid4(),
        product_id=ticket_product.id,
        name="Ticket",
        max_use=2,
        expiration=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(ticket_generator)

    global ticket
    ticket = models_cdr.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        product_variant_id=ticket_variant.id,
        generator_id=ticket_generator.id,
        name="Ticket",
        user_id=cdr_user.id,
        scan_left=1,
        tags="",
        expiration=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(ticket)


def test_get_all_cdr_users_seller(client: TestClient):
    response = client.get(
        "/cdr/users/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(cdr_user.id) in [x["id"] for x in response.json()]


def test_get_all_cdr_users_user(client: TestClient):
    response = client.get(
        "/cdr/users/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_all_cdr_pending_users_seller(client: TestClient):
    response = client.get(
        "/cdr/users/pending",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert str(cdr_user_with_curriculum_with_non_validated_purchase.id) in [
        x["id"] for x in body
    ]


def test_get_all_cdr_pending_users_user(client: TestClient):
    response = client.get(
        "/cdr/users/pending",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_cdr_user_seller(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={
            "nickname": "surnom",
            "promo": 2023,
            "floor": "Autre",
            "phone": "+330606060606",
            "birthday": "1999-01-01",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_cdr_user_seller_with_non_ecl_email(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={"email": "some.email@test.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ECL email address."}


def test_update_cdr_user_seller_with_already_existing_email(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={"email": "cdr_admin@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "A user already exist with this email address"}


def test_update_cdr_user_seller_email(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={"email": "some.email@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_cdr_user_seller_wrong_user(client: TestClient):
    response = client.patch(
        f"/cdr/users/{uuid.uuid4()!s}",
        json={"nickname": "surnom"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_update_cdr_user_user(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={"nickname": "surnom"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_cdr_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(cdr_user.id) == response.json()["id"]


def test_get_all_sellers_admin(client: TestClient):
    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_all_sellers_user(client: TestClient):
    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_my_sellers_seller(client: TestClient):
    response = client.get(
        "/cdr/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_my_sellers_user(client: TestClient):
    response = client.get(
        "/cdr/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_my_sellers_admin_cdr(client: TestClient):
    response = client.get(
        "/cdr/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    # An admin cdr should have access to all sellers
    assert len(response.json()) == 3


def test_get_online_sellers(client: TestClient):
    response = client.get(
        "/cdr/online/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_seller.id) in [x["id"] for x in response.json()]
    assert str(seller.id) not in [x["id"] for x in response.json()]


def test_create_seller_admin(client: TestClient):
    response = client.post(
        "/cdr/sellers/",
        json={
            "name": "Seller créé",
            "group_id": str(GroupType.ph.value),
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    seller_id = uuid.UUID(response.json()["id"])

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller_id) in [x["id"] for x in response.json()]


def test_create_seller_not_admin(client: TestClient):
    response = client.post(
        "/cdr/sellers/",
        json={
            "name": "Seller créé",
            "group_id": str(GroupType.cinema.value),
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert "Seller créé" not in [x["id"] for x in response.json()]


def test_patch_seller_admin(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == "Seller modifié"


def test_patch_seller_wrong_id(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{uuid.uuid4()}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_seller_wrong_seller(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}",
        json={
            "someparameter": "error",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "You must specify at least one field to update",
    }

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == "Seller modifié"


def test_patch_seller_not_admin(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == seller.name


def test_delete_seller_admin(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{empty_seller.id!s}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(empty_seller.id) not in [x["id"] for x in response.json()]


def test_delete_seller_has_product(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_delete_seller_not_admin(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{empty_seller.id!s}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_all_products(client: TestClient):
    response = client.get(
        "/cdr/products/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]
    assert str(product.id) in [x["id"] for x in response.json()]


def test_get_products_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_get_products_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_all_online_products(client: TestClient):
    response = client.get(
        "/cdr/online/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]
    assert str(product.id) not in [x["id"] for x in response.json()]


def test_get_available_online_products(client: TestClient):
    response = client.get(
        f"/cdr/online/sellers/{online_seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]


def test_get_available_online_products_no_product(client: TestClient):
    response = client.get(
        f"/cdr/online/sellers/{seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_product_seller(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/",
        json={
            "name_fr": "Produit créé",
            "name_en": "Created product",
            "available_online": False,
            "product_constraints": [str(product.id)],
            "document_constraints": [str(document.id)],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    product_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product_id) in [x["id"] for x in response.json()]


def test_create_product_user(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/",
        json={
            "name_fr": "Produit créé",
            "name_en": "Created product",
            "available_online": False,
            "product_constraints": [],
            "document_constraints": [],
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert "Produit créé" in [x["name_fr"] for x in response.json()]


def test_patch_product_seller(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "name_fr": "Produit modifié",
            "product_constraints": [str(product.id)],
            "document_constraints": [str(document.id)],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert x["name_fr"] == "Produit modifié"


def test_patch_product_wrong_product(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "esytyd": "Produit modifié",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "You must specify at least one field to update",
    }


def test_patch_product_user(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "name_fr": "Produit modifié",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert x["name_fr"] == product.name_fr


def test_delete_product_seller(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{empty_product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(empty_product.id) not in [x["id"] for x in response.json()]


def test_delete_product_has_variant(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_delete_product_user(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{empty_product.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_delete_document_used(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id}/documents/{document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_product_variant_seller(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "year": year,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    variant_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(variant_id) in [y["id"] for y in x["variants"]]


def test_create_product_variant_user(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée par user",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "year": year,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert "Variante créée par user" not in [
                y["name_fr"] for y in x["variants"]
            ]


def test_patch_product_variant_seller(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
            "allowed_curriculum": [str(curriculum.id)],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(variant.id) in [y["id"] for y in x["variants"]]
            for y in x["variants"]:
                if y["id"] == variant.id:
                    assert y["name_fr"] == "Variante modifiée"
                    assert y["allowed_curriculum"] == [str(curriculum.id)]


def test_patch_product_variant_wrong_product(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "xrsyed": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "You must specify at least one field to update",
    }


def test_patch_product_variant_wrong_id(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{uuid.uuid4()}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_product_variant_other_product_variant(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{online_product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_product_variant_user(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(variant.id) in [y["id"] for y in x["variants"]]
            for y in x["variants"]:
                if y["id"] == variant.id:
                    assert y["name_fr"] == "Variante modifiée"


def test_delete_product_variant_user(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{empty_variant.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(empty_variant.id) in [y["id"] for y in x["variants"]]


def test_delete_product_variant_seller(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{empty_variant.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(empty_variant.id) not in [y["id"] for y in x["variants"]]


def test_get_all_documents_admin(client: TestClient):
    response = client.get(
        "/cdr/documents/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_all_documents_seller(client: TestClient):
    response = client.get(
        "/cdr/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_all_documents_user(client: TestClient):
    response = client.get(
        "/cdr/documents/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_documents_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_documents_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_documents_other_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{online_seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["id"] for x in response.json()]


def test_create_document_seller(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    document_id = uuid.UUID(response.json()["id"])
    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document_id) in [x["id"] for x in response.json()]


def test_create_document_user(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé par user",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert "Document créé par user" not in [x["name"] for x in response.json()]


def test_delete_document_user(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id}/documents/{unused_document.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(unused_document.id) in [x["id"] for x in response.json()]


def test_delete_document_seller(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id}/documents/{unused_document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(unused_document.id) not in [x["id"] for x in response.json()]


def test_get_purchases_by_user_id_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_wrong_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_purchases_by_user_id_other_user_purchase(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_my_purchases(client: TestClient):
    response = client.get(
        "/cdr/me/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_other_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_purchases_by_user_id_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_other_seller_purchase(
    client: TestClient,
):
    response = client.get(
        f"/cdr/sellers/{online_seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_other_user_purchase(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_create_purchase_cdr_not_started(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_purchase_cdr_not_started(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_signature_cdr_not_started(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_payment_not_started(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_user.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_get_status(client: TestClient):
    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.pending


def test_change_status_user(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_change_status_admin_online(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.online


def test_change_status_admin_onsite(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.onsite


def test_update_cdr_user_seller_onsite(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_user.id}",
        json={"nickname": "surnom_onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_change_status_admin_pending_not_closed(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "pending"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.onsite


def test_delete_product_cdr_started(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_product_variant_cdr_started(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "price": "700",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_product_variant_cdr_started(client: TestClient):
    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_purchase_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) not in [x["product_variant_id"] for x in response.json()]


def test_create_purchase_seller(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_create_purchase_wrong_id(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{uuid.uuid4()}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_create_purchase_other_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{uuid.uuid4()}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_purchase_seller(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert x["quantity"] == 2


def test_patch_purchase_wrong_purchase(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "erstrdyfgu": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 422


def test_patch_purchase_wrong_purchase_id(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{empty_variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_purchase_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_signature_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_user.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["document_id"] for x in response.json()]


def test_create_signature_seller(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["document_id"] for x in response.json()]


def test_validate_purchase_seller(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert not x["validated"]


def test_validate_purchase_admin(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert x["validated"]


def test_delete_purchase_validates(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_unvalidate_purchase(client: TestClient):
    response = client.patch(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/validated/?validated=False",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert not x["validated"]


def test_delete_purchase_user(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_delete_purchase_admin(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) not in [x["product_variant_id"] for x in response.json()]


def test_delete_purchase_wrong_variant(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/purchases/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_get_signatures_by_user_id_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_other_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_signatures_by_user_id_admin(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_other_signature(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_other_seller(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{online_seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_other_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_create_signature_wrong_document(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/signatures/{uuid.uuid4()}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_create_signature_numeric_no_id(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.numeric,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_signature_not_admin(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["document_id"] for x in response.json()]


def test_delete_signature_admin(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["document_id"] for x in response.json()]


def test_delete_signature_wrong_signature(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_admin.id}/signatures/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_get_curriculums(client: TestClient):
    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum.id) in [x["id"] for x in response.json()]


def test_create_curriculum_not_admin(client: TestClient):
    response = client.post(
        "/cdr/curriculums/",
        json={
            "name": "Cursus créé par user",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert "Cursus créé par user" not in [x["name"] for x in response.json()]


def test_create_curriculum_admin(client: TestClient):
    response = client.post(
        "/cdr/curriculums/",
        json={
            "name": "Cursus créé",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    curriculum_id = uuid.UUID(response.json()["id"])

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum_id) in [x["id"] for x in response.json()]


def test_delete_curriculum_not_admin(client: TestClient):
    response = client.delete(
        f"/cdr/curriculums/{unused_curriculum.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(unused_curriculum.id) in [x["id"] for x in response.json()]


def test_delete_curriculum_admin(client: TestClient):
    response = client.delete(
        f"/cdr/curriculums/{unused_curriculum.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(unused_curriculum.id) not in [x["id"] for x in response.json()]


def test_delete_curriculum_wrong_id(client: TestClient):
    response = client.delete(
        f"/cdr/curriculums/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_create_curriculum_membership_wrong_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_curriculum_membership_user(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 201


def test_delete_curriculum_membership_wrong_user(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_curriculum_membership_user(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 204


def test_delete_curriculum_membership_wrong_curriculum(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_get_payments_by_user_id_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(payment.id) in [x["id"] for x in response.json()]


def test_get_payments_by_user_id_wrong_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_payments_by_user_id_other_user_payment(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(payment.id) not in [x["id"] for x in response.json()]


def test_create_payment_not_admin(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_admin.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert 12345 not in [x["total"] for x in response.json()]


def test_create_payment_admin(client: TestClient):
    response = client.post(
        f"/cdr/users/{cdr_user.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    payment_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment_id) in [x["id"] for x in response.json()]


def test_delete_payment_not_admin(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment.id) in [x["id"] for x in response.json()]


def test_delete_payment_wrong_id(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id}/payments/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_delete_payment_wrong_user(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_bde.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_delete_payment_admin(client: TestClient):
    response = client.delete(
        f"/cdr/users/{cdr_user.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment.id) not in [x["id"] for x in response.json()]


def test_change_status_admin_closed(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.closed


def test_create_product_closed(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/",
        json={
            "name_fr": "Produit créé",
            "name_en": "Created product",
            "available_online": False,
            "product_constraints": [],
            "document_constraints": [],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_product_variant_closed(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "year": year,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_document_closed(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_curriculum_closed(client: TestClient):
    response = client.post(
        "/cdr/curriculums/",
        json={
            "name": "Cursus créé",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_change_status_admin_online_not_pending(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.closed


def test_change_status_admin_pending(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "pending"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.pending


def test_change_status_admin_onsite_not_online(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.pending


def test_change_status_admin_closed_not_onsite(client: TestClient):
    response = client.patch(
        "/cdr/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.pending


async def test_pay(mocker: MockerFixture, client: TestClient):
    variant_new = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(variant_new)
    purchase_bde = models_cdr.Purchase(
        user_id=cdr_bde.id,
        product_variant_id=variant_new.id,
        quantity=5,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase_bde)

    response = client.post(
        "/cdr/pay/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["url"] == "https://some.url.fr/checkout"

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {"amount": 500, "id": 123},
            "metadata": {
                "hyperion_checkout_id": "81c9ad91-f415-494a-96ad-87bf647df82c",
                "secret": "checkoutsecret",
            },
        },
    )
    assert response.status_code == 204


def test_get_user_tickets(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/tickets/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(ticket.id) in [x["id"] for x in response.json()]
    assert True not in ["secret" in x for x in response.json()]


def test_get_user_tickets_other_user(client: TestClient):
    response = client.get(
        f"/cdr/users/{cdr_user.id}/tickets/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_ticket_secret(client: TestClient):
    response = client.get(
        f"/cdr/users/me/tickets/{ticket.id}/secret/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["qr_code_secret"] == str(ticket.secret)


def test_get_ticket_secret_other_user(client: TestClient):
    response = client.get(
        f"/cdr/users/me/tickets/{ticket.id}/secret/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_get_ticket_secret_wrong_id(client: TestClient):
    response = client.get(
        f"/cdr/users/me/tickets/{uuid.uuid4()}/secret/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_get_ticket_by_secret(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(ticket.id)


def test_get_ticket_by_secret_user(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_ticket_by_secret_wrong_id(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_get_ticket_by_secret_wrong_product(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_scan_ticket(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["scan_left"] == 0
    assert "bus 2" in response.json()["tags"]


def test_scan_ticket_user(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_scan_ticket_wrong_id(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{uuid.uuid4()}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_scan_ticket_wrong_product(client: TestClient):
    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{product.id}/tickets/{ticket_generator.id}/{ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


async def test_scan_ticket_no_scan_left(client: TestClient):
    no_scan_ticket = models_cdr.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        generator_id=ticket_generator.id,
        name="Ticket",
        product_variant_id=ticket_variant.id,
        user_id=cdr_user.id,
        scan_left=0,
        tags="",
        expiration=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(no_scan_ticket)

    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{no_scan_ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


async def test_scan_ticket_expired(client: TestClient):
    expired_ticket = models_cdr.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        name="Ticket",
        generator_id=ticket_generator.id,
        product_variant_id=ticket_variant.id,
        user_id=cdr_user.id,
        scan_left=1,
        tags="",
        expiration=datetime.now(UTC) - timedelta(days=1),
    )
    await add_object_to_db(expired_ticket)

    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/{expired_ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_ticket_tags(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tags/{ticket_generator.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert "bus 2" in response.json()


def test_get_ticket_list(client: TestClient):
    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{ticket_product.id}/tickets/{ticket_generator.id}/lists/Bus 2/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert str(cdr_user.id) in [user["id"] for user in response.json()]


async def test_validate_purchase(client: TestClient):
    product_membership = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
        related_membership_id=association_membership.id,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(product_membership)
    product_membership_to_purchase = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
        related_membership_id=association_membership.id,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(product_membership_to_purchase)
    product_2 = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
        year=year,
        needs_validation=True,
    )
    await add_object_to_db(product_2)
    variant_to_validate = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product_membership_to_purchase.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(variant_to_validate)
    variant_purchased = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product_2.id,
        name_fr="Variante purchased",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        year=year,
    )
    await add_object_to_db(variant_purchased)
    purchase_product_constraint = models_cdr.ProductConstraint(
        product_id=product_membership_to_purchase.id,
        product_constraint_id=product_2.id,
    )
    await add_object_to_db(purchase_product_constraint)
    purchase = models_cdr.Purchase(
        user_id=cdr_user.id,
        product_variant_id=variant_purchased.id,
        quantity=2,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase)
    purchase_to_validate = models_cdr.Purchase(
        user_id=cdr_user.id,
        product_variant_id=variant_to_validate.id,
        quantity=2,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase_to_validate)
    membership = models_memberships.CoreAssociationUserMembership(
        id=uuid.uuid4(),
        user_id=cdr_user.id,
        association_membership_id=association_membership.id,
        start_date=date(2022, 9, 1),
        end_date=datetime.now(UTC).date() + timedelta(days=100),
    )
    await add_object_to_db(membership)

    response = client.patch(
        f"/cdr/users/{cdr_user.id}/purchases/{variant_to_validate.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.delete(
        f"/cdr/users/{cdr_user.id}/purchases/{variant_purchased.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.patch(
        f"/cdr/users/{cdr_user.id}/purchases/{variant_to_validate.id}/validated/?validated=False",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.delete(
        f"/cdr/users/{cdr_user.id}/purchases/{variant_purchased.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_create_customdata_field(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id}/products/{product.id}/data/",
        json={"name": "Chambre", "can_user_answer": False},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


def test_create_customdata_field_user(client: TestClient):
    response = client.post(
        f"/cdr/sellers/{seller.id}/products/{product.id}/data/",
        json={"name": "Chambre", "can_user_answer": False},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_delete_customdata_field(client: TestClient):
    field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
        can_user_answer=False,
    )
    await add_object_to_db(field)

    response = client.delete(
        f"/cdr/sellers/{seller.id}/products/{product.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller.id}/products/{product.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


async def test_create_customdata(client: TestClient):
    customdata_field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Field",
        can_user_answer=False,
    )
    await add_object_to_db(customdata_field)
    response = client.post(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{customdata_field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


async def test_create_customdata_user(client: TestClient):
    customdata_field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Field",
        can_user_answer=False,
    )
    await add_object_to_db(customdata_field)
    response = client.post(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{customdata_field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_update_customdata(client: TestClient):
    field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Edit",
        can_user_answer=False,
    )
    await add_object_to_db(field)
    customdata = models_cdr.CustomData(
        field_id=field.id,
        user_id=cdr_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "ABCD"


async def test_update_customdata_user(client: TestClient):
    field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Edit",
        can_user_answer=False,
    )
    await add_object_to_db(field)
    customdata = models_cdr.CustomData(
        field_id=field.id,
        user_id=cdr_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.patch(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_delete_customdata(client: TestClient):
    field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
        can_user_answer=False,
    )
    await add_object_to_db(field)
    customdata = models_cdr.CustomData(
        field_id=field.id,
        user_id=cdr_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.delete(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


async def test_customdata_deletion_on_purchase_deletion(client: TestClient):
    field = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
        can_user_answer=False,
    )
    await add_object_to_db(field)
    customdata = models_cdr.CustomData(
        field_id=field.id,
        user_id=cdr_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.delete(
        f"/cdr/users/{cdr_user.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id}/products/{product.id}/users/{cdr_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.ticket import models_ticket
from app.modules.purchases import models_purchases
from app.modules.purchases.types_purchases import (
    DocumentSignatureType,
    PaymentType,
    PurchasesStatus,
)
from app.types.membership import AvailableAssociationMembership
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

purchases_admin: models_core.CoreUser
purchases_bde: models_core.CoreUser
purchases_user: models_core.CoreUser

token_admin: str
token_bde: str
token_user: str

seller: models_purchases.Seller
online_seller: models_purchases.Seller
empty_seller: models_purchases.Seller

product: models_purchases.PurchasesProduct
online_product: models_purchases.PurchasesProduct
empty_product: models_purchases.PurchasesProduct
usable_product: models_purchases.PurchasesProduct
ticket_product: models_purchases.PurchasesProduct

document: models_purchases.Document
unused_document: models_purchases.Document
other_document: models_purchases.Document

document_constraint: models_purchases.DocumentConstraint
product_constraint: models_purchases.ProductConstraint

variant: models_purchases.ProductVariant
empty_variant: models_purchases.ProductVariant
ticket_variant: models_purchases.ProductVariant

curriculum: models_purchases.Curriculum
unused_curriculum: models_purchases.Curriculum

purchases_user_with_curriculum_with_non_validated_purchase: models_core.CoreUser

purchase: models_purchases.Purchase

signature: models_purchases.Signature
signature_admin: models_purchases.Signature

payment: models_purchases.Payment

membership: models_core.CoreAssociationMembership

ticket: models_ticket.Ticket
ticket_generator: models_ticket.TicketGenerator


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global purchases_admin
    purchases_admin = await create_user_with_groups(
        [GroupType.student, GroupType.admin_purchases],
        email="purchases_admin@etu.ec-lyon.fr",
    )

    global token_admin
    token_admin = create_api_access_token(purchases_admin)

    global purchases_bde
    purchases_bde = await create_user_with_groups([GroupType.student, GroupType.BDE])

    global token_bde
    token_bde = create_api_access_token(purchases_bde)

    global purchases_user
    purchases_user = await create_user_with_groups([GroupType.student])

    global token_user
    token_user = create_api_access_token(purchases_user)

    global seller
    seller = models_purchases.Seller(
        id=uuid.uuid4(),
        name="BDE",
        group_id=str(GroupType.BDE.value),
        order=5,
    )
    await add_object_to_db(seller)

    global online_seller
    online_seller = models_purchases.Seller(
        id=uuid.uuid4(),
        name="CAA",
        group_id=str(GroupType.CAA.value),
        order=12,
    )
    await add_object_to_db(online_seller)

    global empty_seller
    empty_seller = models_purchases.Seller(
        id=uuid.uuid4(),
        name="Seller Vide",
        group_id=str(GroupType.cinema.value),
        order=99,
    )
    await add_object_to_db(empty_seller)

    global product
    product = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit",
        name_en="Product",
        description_fr="Un Produit",
        description_en="A Product",
        available_online=False,
    )
    await add_object_to_db(product)

    global online_product
    online_product = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=online_seller.id,
        name_fr="Produit en ligne",
        name_en="Online Product",
        description_fr="Un Produit disponible en ligne",
        description_en="An online available Product",
        available_online=True,
    )
    await add_object_to_db(online_product)

    global empty_product
    empty_product = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit sans variante",
        name_en="Unused product",
        available_online=False,
    )
    await add_object_to_db(empty_product)

    global usable_product
    usable_product = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit utilisable",
        name_en="Usable product",
        available_online=False,
    )
    await add_object_to_db(usable_product)

    global document
    document = models_purchases.Document(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name="Document à signer",
    )
    await add_object_to_db(document)

    global unused_document
    unused_document = models_purchases.Document(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name="Document non utilisé",
    )
    await add_object_to_db(unused_document)

    global other_document
    other_document = models_purchases.Document(
        id=uuid.uuid4(),
        seller_id=online_seller.id,
        name="Document non utilisé",
    )
    await add_object_to_db(other_document)

    global document_constraint
    document_constraint = models_purchases.DocumentConstraint(
        product_id=product.id,
        document_id=document.id,
    )
    await add_object_to_db(document_constraint)

    global product_constraint
    product_constraint = models_purchases.ProductConstraint(
        product_id=product.id,
        product_constraint_id=online_product.id,
    )
    await add_object_to_db(product_constraint)

    global variant
    variant = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(variant)

    global empty_variant
    empty_variant = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante vide",
        name_en="Empty variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(empty_variant)

    global curriculum
    curriculum = models_purchases.Curriculum(
        id=uuid.uuid4(),
        name="Ingénieur généraliste",
    )
    await add_object_to_db(curriculum)

    global unused_curriculum
    unused_curriculum = models_purchases.Curriculum(
        id=uuid.uuid4(),
        name="Ingénieur généraliste inutile",
    )
    await add_object_to_db(unused_curriculum)

    purchases_user_with_curriculum_without_purchase = await create_user_with_groups(
        [GroupType.student],
    )
    curriculum_membership = models_purchases.CurriculumMembership(
        user_id=purchases_user_with_curriculum_without_purchase.id,
        curriculum_id=curriculum.id,
    )
    await add_object_to_db(curriculum_membership)

    global purchases_user_with_curriculum_with_non_validated_purchase
    purchases_user_with_curriculum_with_non_validated_purchase = (
        await create_user_with_groups(
            [GroupType.student],
        )
    )
    curriculum_membership_for_user_with_curriculum_with_non_validated_purchase = (
        models_purchases.CurriculumMembership(
            user_id=purchases_user_with_curriculum_with_non_validated_purchase.id,
            curriculum_id=curriculum.id,
        )
    )
    await add_object_to_db(
        curriculum_membership_for_user_with_curriculum_with_non_validated_purchase,
    )
    purchase_for_user_with_curriculum_with_non_validated_purchase = (
        models_purchases.Purchase(
            user_id=purchases_user_with_curriculum_with_non_validated_purchase.id,
            product_variant_id=variant.id,
            quantity=1,
            validated=False,
            purchased_on=datetime.now(UTC),
            paid=False
        )
    )
    await add_object_to_db(
        purchase_for_user_with_curriculum_with_non_validated_purchase,
    )

    global purchase
    purchase = models_purchases.Purchase(
        user_id=purchases_user.id,
        product_variant_id=variant.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
        paid=False,
    )
    await add_object_to_db(purchase)

    global signature
    signature = models_purchases.Signature(
        user_id=purchases_user.id,
        document_id=document.id,
        signature_type=DocumentSignatureType.numeric,
        numeric_signature_id="somedocumensoid",
    )
    await add_object_to_db(signature)

    global payment
    payment = models_purchases.Payment(
        id=uuid.uuid4(),
        user_id=purchases_user.id,
        total=5000,
        payment_type=PaymentType.cash,
    )
    await add_object_to_db(payment)

    global membership
    membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        user_id=purchases_user.id,
        membership=AvailableAssociationMembership.aeecl,
        start_date=date(2022, 9, 1),
        end_date=date(2026, 9, 1),
    )
    await add_object_to_db(membership)

    global ticket_product
    ticket_product = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit a ticket",
        name_en="Usable product",
        available_online=False,
    )
    await add_object_to_db(ticket_product)

    global ticket_variant
    ticket_variant = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=ticket_product.id,
        name_fr="variante a ticket",
        name_en="Empty variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(ticket_variant)

    global ticket_generator
    ticket_generator = models_ticket.TicketGenerator(
        id=uuid.uuid4(),
        name="Ticket",
        max_use=2,
        expiration=datetime.now(UTC) + timedelta(days=1),
        scanner_group_id=seller.group_id,
    )
    await add_object_to_db(ticket_generator)

    global ticket
    ticket = models_ticket.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        generator_id=ticket_generator.id,
        name="Ticket",
        user_id=purchases_user.id,
        scan_left=1,
        tags="",
        expiration=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(ticket)


def test_get_all_purchases_users_seller(client: TestClient):
    response = client.get(
        "/purchases/users/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchases_user.id) in [x["id"] for x in response.json()]


def test_get_all_purchases_users_user(client: TestClient):
    response = client.get(
        "/purchases/users/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_all_purchases_pending_users_seller(client: TestClient):
    response = client.get(
        "/purchases/users/pending",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert str(purchases_user_with_curriculum_with_non_validated_purchase.id) in [
        x["id"] for x in body
    ]


def test_get_all_purchases_pending_users_user(client: TestClient):
    response = client.get(
        "/purchases/users/pending",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_update_purchases_user_seller(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
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


def test_update_purchases_user_seller_with_non_ecl_email(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
        json={"email": "some.email@test.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ECL email address."}


def test_update_purchases_user_seller_with_already_existing_email(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
        json={"email": "purchases_admin@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "A user already exist with this email address"}


def test_update_purchases_user_seller_email(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
        json={"email": "some.email@etu.ec-lyon.fr"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_update_purchases_user_seller_wrong_user(client: TestClient):
    response = client.patch(
        f"/purchases/users/{uuid.uuid4()!s}",
        json={"nickname": "surnom"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_update_purchases_user_user(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
        json={"nickname": "surnom"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_purchases_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchases_user.id) == response.json()["id"]


def test_get_all_sellers_admin(client: TestClient):
    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_all_sellers_user(client: TestClient):
    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_my_sellers_seller(client: TestClient):
    response = client.get(
        "/purchases/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_my_sellers_user(client: TestClient):
    response = client.get(
        "/purchases/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_my_sellers_admin_purchases(client: TestClient):
    response = client.get(
        "/purchases/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    # An admin purchases should have access to all sellers
    assert len(response.json()) == 3


def test_get_online_sellers(client: TestClient):
    response = client.get(
        "/purchases/online/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_seller.id) in [x["id"] for x in response.json()]
    assert str(seller.id) not in [x["id"] for x in response.json()]


def test_create_seller_admin(client: TestClient):
    response = client.post(
        "/purchases/sellers/",
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
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller_id) in [x["id"] for x in response.json()]


def test_create_seller_not_admin(client: TestClient):
    response = client.post(
        "/purchases/sellers/",
        json={
            "name": "Seller créé",
            "group_id": str(GroupType.cinema.value),
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert "Seller créé" not in [x["id"] for x in response.json()]


def test_patch_seller_admin(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == "Seller modifié"


def test_patch_seller_wrong_id(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{uuid.uuid4()}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_patch_seller_wrong_seller(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id}",
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
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == "Seller modifié"


def test_patch_seller_not_admin(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller.id:
            assert x["name"] == seller.name


def test_delete_seller_admin(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{empty_seller.id!s}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(empty_seller.id) not in [x["id"] for x in response.json()]


def test_delete_seller_has_product(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_delete_seller_not_admin(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{empty_seller.id!s}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]


def test_get_all_products(client: TestClient):
    response = client.get(
        "/purchases/products/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]
    assert str(product.id) in [x["id"] for x in response.json()]


def test_get_products_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_get_products_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_all_online_products(client: TestClient):
    response = client.get(
        "/purchases/online/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]
    assert str(product.id) not in [x["id"] for x in response.json()]


def test_get_available_online_products(client: TestClient):
    response = client.get(
        f"/purchases/online/sellers/{online_seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]


def test_get_available_online_products_no_product(client: TestClient):
    response = client.get(
        f"/purchases/online/sellers/{seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_product_seller(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/",
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
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product_id) in [x["id"] for x in response.json()]


def test_create_product_user(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/",
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
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert "Produit créé" in [x["name_fr"] for x in response.json()]


def test_patch_product_seller(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "name_fr": "Produit modifié",
            "product_constraints": [str(product.id)],
            "document_constraints": [str(document.id)],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert x["name_fr"] == "Produit modifié"


def test_patch_product_wrong_product(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
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
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "name_fr": "Produit modifié",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert x["name_fr"] == product.name_fr


def test_delete_product_seller(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{empty_product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(empty_product.id) not in [x["id"] for x in response.json()]


def test_delete_product_has_variant(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_delete_product_user(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{empty_product.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]


def test_delete_document_used(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id}/documents/{document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_product_variant_seller(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "needs_validation": True,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    variant_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(variant_id) in [y["id"] for y in x["variants"]]


def test_create_product_variant_user(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée par user",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "needs_validation": True,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
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
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
            "allowed_curriculum": [str(curriculum.id)],
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
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
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
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
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{uuid.uuid4()}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_product_variant_other_product_variant(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{online_product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_product_variant_user(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
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
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{empty_variant.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(empty_variant.id) in [y["id"] for y in x["variants"]]


def test_delete_product_variant_seller(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{empty_variant.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == str(product.id):
            assert str(empty_variant.id) not in [y["id"] for y in x["variants"]]


def test_get_all_documents_admin(client: TestClient):
    response = client.get(
        "/purchases/documents/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_all_documents_seller(client: TestClient):
    response = client.get(
        "/purchases/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_all_documents_user(client: TestClient):
    response = client.get(
        "/purchases/documents/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_documents_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]


def test_get_documents_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_documents_other_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{online_seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["id"] for x in response.json()]


def test_create_document_seller(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    document_id = uuid.UUID(response.json()["id"])
    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document_id) in [x["id"] for x in response.json()]


def test_create_document_user(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé par user",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert "Document créé par user" not in [x["name"] for x in response.json()]


def test_delete_document_user(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id}/documents/{unused_document.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(unused_document.id) in [x["id"] for x in response.json()]


def test_delete_document_seller(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id}/documents/{unused_document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(unused_document.id) not in [x["id"] for x in response.json()]


def test_get_purchases_by_user_id_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_wrong_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_purchases_by_user_id_other_user_purchase(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_my_purchases(client: TestClient):
    response = client.get(
        "/purchases/me/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_other_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_purchases_by_user_id_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_user.id}/purchases/",
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
        f"/purchases/sellers/{online_seller.id}/users/{purchases_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id_other_user_purchase(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_create_purchase_purchases_not_started(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_purchase_purchases_not_started(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_signature_purchases_not_started(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_payment_not_started(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_get_status(client: TestClient):
    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.pending


def test_change_status_user(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_change_status_admin_online(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.online


def test_change_status_admin_onsite(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.onsite


def test_update_purchases_user_seller_onsite(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_user.id}",
        json={"nickname": "surnom_onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_change_status_admin_pending_not_closed(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "pending"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.onsite


def test_delete_product_purchases_started(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_patch_product_variant_purchases_started(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_product_variant_purchases_started(client: TestClient):
    response = client.delete(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_purchase_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) not in [x["product_variant_id"] for x in response.json()]


def test_create_purchase_seller(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_create_purchase_wrong_id(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{uuid.uuid4()}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_create_purchase_other_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{uuid.uuid4()}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_purchase_seller(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert x["quantity"] == 2


def test_patch_purchase_wrong_purchase(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "erstrdyfgu": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 422


def test_patch_purchase_wrong_purchase_id(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{empty_variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_patch_purchase_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_signature_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["document_id"] for x in response.json()]


def test_create_signature_seller(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["document_id"] for x in response.json()]


def test_validate_purchase_seller(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert not x["validated"]


def test_validate_purchase_admin(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert x["validated"]


def test_delete_purchase_validates(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_unvalidate_purchase(client: TestClient):
    response = client.patch(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/validated/?validated=False",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]
    for x in response.json():
        if x["product_variant_id"] == str(variant.id):
            assert not x["validated"]


def test_delete_purchase_user(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]


def test_delete_purchase_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/purchases/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(variant.id) not in [x["product_variant_id"] for x in response.json()]


def test_delete_purchase_wrong_variant(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/purchases/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_get_signatures_by_user_id_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_other_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_signatures_by_user_id_admin(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_other_signature(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_other_seller(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{online_seller.id}/users/{purchases_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id_other_user(client: TestClient):
    response = client.get(
        f"/purchases/sellers/{seller.id}/users/{purchases_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_create_signature_wrong_document(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/signatures/{uuid.uuid4()}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_create_signature_numeric_no_id(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.numeric,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_signature_not_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/signatures/{document.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["document_id"] for x in response.json()]


def test_delete_signature_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/signatures/{document.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_admin.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["document_id"] for x in response.json()]


def test_delete_signature_wrong_signature(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_admin.id}/signatures/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_get_curriculums(client: TestClient):
    response = client.get(
        "/purchases/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum.id) in [x["id"] for x in response.json()]


def test_create_curriculum_not_admin(client: TestClient):
    response = client.post(
        "/purchases/curriculums/",
        json={
            "name": "Cursus créé par user",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert "Cursus créé par user" not in [x["name"] for x in response.json()]


def test_create_curriculum_admin(client: TestClient):
    response = client.post(
        "/purchases/curriculums/",
        json={
            "name": "Cursus créé",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    curriculum_id = uuid.UUID(response.json()["id"])

    response = client.get(
        "/purchases/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum_id) in [x["id"] for x in response.json()]


def test_delete_curriculum_not_admin(client: TestClient):
    response = client.delete(
        f"/purchases/curriculums/{unused_curriculum.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/curriculums/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(unused_curriculum.id) in [x["id"] for x in response.json()]


def test_delete_curriculum_admin(client: TestClient):
    response = client.delete(
        f"/purchases/curriculums/{unused_curriculum.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/curriculums/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(unused_curriculum.id) not in [x["id"] for x in response.json()]


def test_delete_curriculum_wrong_id(client: TestClient):
    response = client.delete(
        f"/purchases/curriculums/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_create_curriculum_membership_wrong_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_curriculum_membership_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 201


def test_delete_curriculum_membership_wrong_user(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_delete_curriculum_membership_user(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 204


def test_delete_curriculum_membership_wrong_curriculum(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id!s}/curriculums/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_get_payments_by_user_id_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(payment.id) in [x["id"] for x in response.json()]


def test_get_payments_by_user_id_wrong_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_payments_by_user_id_other_user_payment(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(payment.id) not in [x["id"] for x in response.json()]


def test_create_payment_not_admin(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_admin.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert 12345 not in [x["total"] for x in response.json()]


def test_create_payment_admin(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    payment_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/purchases/users/{purchases_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment_id) in [x["id"] for x in response.json()]


def test_delete_payment_not_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment.id) in [x["id"] for x in response.json()]


def test_delete_payment_wrong_id(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/payments/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_delete_payment_wrong_user(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_bde.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_delete_payment_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/payments/{payment.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment.id) not in [x["id"] for x in response.json()]


def test_get_memberships_by_user_id_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/memberships/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(membership.id) in [x["id"] for x in response.json()]


def test_get_memberships_by_user_id_other_user(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_bde.id}/memberships/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_memberships_by_user_id_admin(client: TestClient):
    response = client.get(
        f"/purchases/users/{purchases_user.id}/memberships/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership.id) in [x["id"] for x in response.json()]


def test_create_membership_user(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id}/memberships/",
        json={
            "membership": AvailableAssociationMembership.useecl,
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_membership_admin(client: TestClient):
    response = client.post(
        f"/purchases/users/{purchases_user.id}/memberships/",
        json={
            "membership": AvailableAssociationMembership.useecl,
            "start_date": str(date(2024, 6, 1)),
            "end_date": str(date(2028, 6, 1)),
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    membership_id = uuid.UUID(response.json()["id"])

    response = client.get(
        f"/purchases/users/{purchases_user.id}/memberships/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership_id) in [x["id"] for x in response.json()]


def test_delete_membership_user(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/memberships/{membership.id}",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/purchases/users/{purchases_user.id}/memberships/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership.id) in [x["id"] for x in response.json()]


def test_delete_membership_wrong_id(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/memberships/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_delete_membership_admin(client: TestClient):
    response = client.delete(
        f"/purchases/users/{purchases_user.id}/memberships/{membership.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/users/{purchases_user.id}/memberships/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(membership.id) not in [x["id"] for x in response.json()]


def test_change_status_admin_closed(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.closed


def test_create_product_closed(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/",
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


def test_patch_product_closed(client: TestClient):
    response = client.patch(
        f"/purchases/sellers/{seller.id!s}/products/{product.id}/",
        json={
            "name_fr": "Produit modifié",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_product_variant_closed(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
            "allowed_curriculum": [str(curriculum.id)],
            "needs_validation": True,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_document_closed(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id}/documents/",
        json={
            "name": "Document créé",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_curriculum_closed(client: TestClient):
    response = client.post(
        "/purchases/curriculums/",
        json={
            "name": "Cursus créé",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_change_status_admin_online_not_pending(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.closed


def test_change_status_admin_pending(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "pending"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.pending


def test_change_status_admin_onsite_not_online(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.pending


def test_change_status_admin_closed_not_onsite(client: TestClient):
    response = client.patch(
        "/purchases/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/purchases/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == PurchasesStatus.pending


async def test_pay(mocker: MockerFixture, client: TestClient):
    variant_new = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(variant_new)
    purchase_bde = models_purchases.Purchase(
        user_id=purchases_bde.id,
        product_variant_id=variant_new.id,
        quantity=5,
        validated=False,
        purchased_on=datetime.now(UTC),
        paid=False,
    )
    await add_object_to_db(purchase_bde)

    response = client.post(
        "/purchases/pay/",
        json={"purchase_ids":[]},
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
        f"/tickets/users/{purchases_user.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(ticket.id) in [x["id"] for x in response.json()]
    assert True not in ["secret" in x for x in response.json()]


def test_get_user_tickets_other_user(client: TestClient):
    response = client.get(
        f"/tickets/users/{purchases_user.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_ticket_secret(client: TestClient):
    response = client.get(
        f"/tickets/{ticket.id}/secret/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["qr_code_secret"] == str(ticket.secret)


def test_get_ticket_secret_other_user(client: TestClient):
    response = client.get(
        f"/tickets/{ticket.id}/secret/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_get_ticket_secret_wrong_id(client: TestClient):
    response = client.get(
        f"/tickets/{uuid.uuid4()}/secret/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 404


def test_get_ticket_by_secret(client: TestClient):
    response = client.get(
        f"/tickets/generator/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(ticket.id)


def test_get_ticket_by_secret_user(client: TestClient):
    response = client.get(
        f"/tickets/generator/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_ticket_by_secret_wrong_id(client: TestClient):
    response = client.get(
        f"/tickets/generator/{ticket_generator.id}/{uuid.uuid4()}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


def test_scan_ticket(client: TestClient):
    response = client.patch(
        f"/tickets/generator/{ticket_generator.id}/{ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/tickets/generator/{ticket_generator.id}/{ticket.secret}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["scan_left"] == 0
    assert "bus 2" in response.json()["tags"]


def test_scan_ticket_user(client: TestClient):
    response = client.patch(
        f"/tickets/generator/{ticket_generator.id}/{ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_scan_ticket_wrong_id(client: TestClient):
    response = client.patch(
        f"/tickets/generator/{ticket_generator.id}/{uuid.uuid4()}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 404


async def test_scan_ticket_no_scan_left(client: TestClient):
    no_scan_ticket = models_ticket.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        generator_id=ticket_generator.id,
        name="Ticket",
        user_id=purchases_user.id,
        scan_left=0,
        tags="",
        expiration=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(no_scan_ticket)

    response = client.patch(
        f"/tickets/generator/{ticket_generator.id}/{no_scan_ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


async def test_scan_ticket_expired(client: TestClient):
    expired_ticket = models_ticket.Ticket(
        id=uuid.uuid4(),
        secret=uuid.uuid4(),
        name="Ticket",
        generator_id=ticket_generator.id,
        user_id=purchases_user.id,
        scan_left=1,
        tags="",
        expiration=datetime.now(UTC) - timedelta(days=1),
    )
    await add_object_to_db(expired_ticket)

    response = client.patch(
        f"/tickets/generator/{ticket_generator.id}/{expired_ticket.secret}/",
        json={"tag": "Bus 2"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_ticket_tags(client: TestClient):
    response = client.get(
        f"/tickets/tags/generator/{ticket_generator.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert "bus 2" in response.json()


def test_get_ticket_list(client: TestClient):
    response = client.get(
        f"/tickets/generator/{ticket_generator.id}/lists/Bus 2/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert str(purchases_user.id) in [user["id"] for user in response.json()]


async def test_validate_purchase(client: TestClient):
    product_membership = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
        related_membership=AvailableAssociationMembership.useecl,
    )
    await add_object_to_db(product_membership)
    product_membership_to_purchase = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
        related_membership=AvailableAssociationMembership.aeecl,
    )
    await add_object_to_db(product_membership_to_purchase)
    product_2 = models_purchases.PurchasesProduct(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name_fr="Produit à adhésion",
        name_en="Product",
        available_online=False,
    )
    await add_object_to_db(product_2)
    variant_to_validate = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=product_membership_to_purchase.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(variant_to_validate)
    variant_purchased = models_purchases.ProductVariant(
        id=uuid.uuid4(),
        product_id=product_2.id,
        name_fr="Variante purchased",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
        needs_validation=False,
    )
    await add_object_to_db(variant_purchased)
    purchase_product_constraint = models_purchases.ProductConstraint(
        product_id=product_membership_to_purchase.id,
        product_constraint_id=product_2.id,
    )
    await add_object_to_db(purchase_product_constraint)
    purchase = models_purchases.Purchase(
        user_id=purchases_user.id,
        product_variant_id=variant_purchased.id,
        quantity=2,
        validated=False,
        purchased_on=datetime.now(UTC),
        paid=False,
    )
    await add_object_to_db(purchase)
    purchase_to_validate = models_purchases.Purchase(
        user_id=purchases_user.id,
        product_variant_id=variant_to_validate.id,
        quantity=2,
        validated=False,
        purchased_on=datetime.now(UTC),
        paid=False,
    )
    await add_object_to_db(purchase_to_validate)
    membership = models_core.CoreAssociationMembership(
        id=uuid.uuid4(),
        user_id=purchases_user.id,
        membership=AvailableAssociationMembership.useecl,
        start_date=date(2022, 9, 1),
        end_date=datetime.now(UTC).date() + timedelta(days=100),
    )
    await add_object_to_db(membership)

    response = client.patch(
        f"/purchases/users/{purchases_user.id}/purchases/{variant_to_validate.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.delete(
        f"/purchases/users/{purchases_user.id}/purchases/{variant_purchased.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403

    response = client.patch(
        f"/purchases/users/{purchases_user.id}/purchases/{variant_to_validate.id}/validated/?validated=False",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.delete(
        f"/purchases/users/{purchases_user.id}/purchases/{variant_purchased.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_create_customdata_field(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id}/products/{product.id}/data/",
        json={"name": "Chambre"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


def test_create_customdata_field_user(client: TestClient):
    response = client.post(
        f"/purchases/sellers/{seller.id}/products/{product.id}/data/",
        json={"name": "Chambre"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_delete_customdata_field(client: TestClient):
    field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
    )
    await add_object_to_db(field)

    response = client.delete(
        f"/purchases/sellers/{seller.id}/products/{product.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/purchases/sellers/{seller.id}/products/{product.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


async def test_create_customdata(client: TestClient):
    customdata_field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Field",
    )
    await add_object_to_db(customdata_field)
    response = client.post(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{customdata_field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201


async def test_create_customdata_user(client: TestClient):
    customdata_field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Field",
    )
    await add_object_to_db(customdata_field)
    response = client.post(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{customdata_field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_update_customdata(client: TestClient):
    field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Edit",
    )
    await add_object_to_db(field)
    customdata = models_purchases.CustomData(
        field_id=field.id,
        user_id=purchases_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.patch(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "ABCD"


async def test_update_customdata_user(client: TestClient):
    field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Edit",
    )
    await add_object_to_db(field)
    customdata = models_purchases.CustomData(
        field_id=field.id,
        user_id=purchases_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.patch(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        json={"value": "ABCD"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


async def test_delete_customdata(client: TestClient):
    field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
    )
    await add_object_to_db(field)
    customdata = models_purchases.CustomData(
        field_id=field.id,
        user_id=purchases_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.delete(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204


async def test_customdata_deletion_on_purchase_deletion(client: TestClient):
    field = models_purchases.CustomDataField(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Supprime",
    )
    await add_object_to_db(field)
    customdata = models_purchases.CustomData(
        field_id=field.id,
        user_id=purchases_user.id,
        value="Edit",
    )
    await add_object_to_db(customdata)

    response = client.delete(
        f"/purchases/users/{purchases_user.id}/purchases/{variant.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/purchases/sellers/{seller.id}/products/{product.id}/users/{purchases_user.id}/data/{field.id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404

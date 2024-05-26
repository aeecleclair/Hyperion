import uuid

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.cdr import models_cdr
from app.modules.cdr.types_cdr import (
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
)
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

cdr_admin: models_core.CoreUser
cdr_bde: models_core.CoreUser
cdr_user: models_core.CoreUser

token_admin: str
token_bde: str
token_user: str

seller: models_cdr.Seller
online_seller: models_cdr.Seller

product: models_cdr.CdrProduct
online_product: models_cdr.CdrProduct

document: models_cdr.Document

variant: models_cdr.ProductVariant

curriculum: models_cdr.Curriculum

purchase: models_cdr.Purchase

signature: models_cdr.Signature

payment: models_cdr.Payment


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global cdr_admin
    cdr_admin = await create_user_with_groups(
        [GroupType.student, GroupType.admin_cdr],
    )

    global token_admin
    token_admin = create_api_access_token(cdr_admin)

    global cdr_bde
    cdr_bde = await create_user_with_groups([GroupType.student, GroupType.BDE])

    global token_bde
    token_bde = create_api_access_token(cdr_bde)

    global cdr_user
    cdr_user = await create_user_with_groups([GroupType.student])

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

    global product
    product = models_cdr.CdrProduct(
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
    online_product = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=online_seller.id,
        name_fr="Produit en ligne",
        name_en="Online Product",
        description_fr="Un Produit disponible en ligne",
        description_en="An online available Product",
        available_online=True,
    )
    await add_object_to_db(online_product)

    global document
    document = models_cdr.Document(
        id=uuid.uuid4(),
        seller_id=seller.id,
        name="Document à signer",
    )
    await add_object_to_db(document)

    global variant
    variant = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
    )
    await add_object_to_db(variant)

    global curriculum
    curriculum = models_cdr.Curriculum(
        id=uuid.uuid4(),
        name="Ingénieur généraliste",
    )
    await add_object_to_db(curriculum)

    global purchase
    purchase = models_cdr.Purchase(
        user_id=cdr_user.id,
        product_variant_id=variant.id,
        quantity=1,
        validated=False,
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
    )
    await add_object_to_db(payment)


def test_get_all_sellers():
    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_my_sellers():
    response = client.get(
        "/cdr/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(seller.id) in [x["id"] for x in response.json()]

    response = client.get(
        "/cdr/users/me/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_online_sellers():
    response = client.get(
        "/cdr/online/sellers/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_seller.id) in [x["id"] for x in response.json()]
    assert str(seller.id) not in [x["id"] for x in response.json()]


def test_create_patch_delete_seller():
    response = client.post(
        "/cdr/sellers/",
        json={
            "name": "Seller crée",
            "group_id": str(GroupType.cinema.value),
            "order": 1,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    seller_id = uuid.UUID(response.json()["id"])

    response = client.post(
        "/cdr/sellers/",
        json={
            "name": "Seller crée",
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
    assert str(seller_id) in [x["id"] for x in response.json()]

    response = client.patch(
        f"/cdr/sellers/{seller_id!s}",
        json={
            "name": "Seller modifié",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.patch(
        f"/cdr/sellers/{seller_id!s}",
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
    assert str(seller_id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == seller_id:
            assert x["name"] == "Seller modifié"

    response = client.delete(
        f"/cdr/sellers/{seller_id!s}",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller_id!s}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/sellers/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(seller_id) not in [x["id"] for x in response.json()]


def test_get_products_by_seller_id():
    response = client.get(
        f"/cdr/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/cdr/sellers/{seller.id}/products",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_available_online_products():
    response = client.get(
        f"/cdr/online/sellers/{online_seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(online_product.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/cdr/online/sellers/{seller.id}/products/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_patch_delete_product():
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/",
        json={
            "name_fr": "Produit crée",
            "name_en": "Created product",
            "available_online": False,
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

    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product_id}/",
        json={
            "name_fr": "Produit modifié",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product_id}/",
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
    assert str(product_id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product_id:
            assert x["name_fr"] == "Produit modifié"

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product_id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product_id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product_id) not in [x["id"] for x in response.json()]

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/",
        json={
            "name_fr": "Produit crée",
            "name_en": "Created product",
            "available_online": False,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_delete_document_constraint():
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/document_constraints/{document.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert str(document.id) in [y["id"] for y in x["document_constraints"]]

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/document_constraints/{document.id!s}/",
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
            assert str(document.id) not in [y["id"] for y in x["document_constraints"]]


def test_create_delete_product_constraint():
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/product_constraints/{online_product.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    response = client.get(
        f"/cdr/sellers/{seller.id!s}/products/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(product.id) in [x["id"] for x in response.json()]
    for x in response.json():
        if x["id"] == product.id:
            assert str(document.id) in [y["id"] for y in x["product_constraints"]]

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/product_constraints/{online_product.id!s}/",
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
            assert str(document.id) not in [y["id"] for y in x["product_constraints"]]

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{online_product.id!s}/product_constraints/{product.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.post(
        f"/cdr/sellers/{online_seller.id!s}/products/{online_product.id!s}/product_constraints/{product.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/product_constraints/{online_product.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/product_constraints/{product.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_create_patch_delete_product_variant():
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
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

    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant_id}/",
        json={
            "name_fr": "Variante modifiée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.patch(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant_id}/",
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
            assert str(variant_id) in [y["id"] for y in x["variants"]]
            for y in x["variants"]:
                if y["id"] == variant_id:
                    assert y["name_fr"] == "Variante modifiée"

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant_id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant_id}/",
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
            assert str(variant_id) not in [y["id"] for y in x["variants"]]

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/",
        json={
            "name_fr": "Variante créée",
            "name_en": "Created variant",
            "enabled": True,
            "price": 5000,
            "unique": True,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_create_delete_allowed_curriculum():
    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

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
                    assert curriculum.id in [z["id"] for z in y["allowed_curriculums"]]

    response = client.delete(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id!s}/curriculums/{curriculum.id!s}/",
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
                    assert curriculum.id not in [
                        z["id"] for z in y["allowed_curriculums"]
                    ]

    response = client.post(
        f"/cdr/sellers/{seller.id!s}/products/{product.id!s}/variants/{variant.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403


def test_get_documents():
    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{online_seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(document.id) not in [x["id"] for x in response.json()]


def test_create_delete_document():
    response = client.post(
        f"/cdr/sellers/{seller.id}/documents/",
        json={
            "name": "Document crée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

    document_id = uuid.UUID(response.json()["id"])

    response = client.post(
        f"/cdr/sellers/{seller.id}/documents/",
        json={
            "name": "Document crée",
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document_id) in [x["id"] for x in response.json()]

    response = client.delete(
        f"/cdr/sellers/{seller.id}/documents/{document_id}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/sellers/{seller.id}/documents/{document_id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/sellers/{seller.id}/documents/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(document_id) not in [x["id"] for x in response.json()]


def test_get_purchases_by_user_id():
    response = client.get(
        f"/cdr/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]

    response = client.get(
        f"/cdr/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_get_purchases_by_user_id_by_seller_id():
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]

    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) in [
        x["product_variant_id"] for x in response.json()
    ]

    response = client.get(
        f"/cdr/sellers/{online_seller.id}/users/{cdr_user.id}/purchases/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]

    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_bde.id}/purchases/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(purchase.product_variant_id) not in [
        x["product_variant_id"] for x in response.json()
    ]


def test_change_status():
    response = client.get(
        "/cdr/status/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == CdrStatus.pending

    response = client.patch(
        "/cdr/status/",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

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


def test_create_update_delete_validate_purchase():
    response = client.patch(
        "/cdr/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.patch(
        "/cdr/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.post(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 1,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

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
    assert str(variant.id) in [x["product_variant_id"] for x in response.json()]

    response = client.patch(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/",
        json={
            "quantity": 2,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
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
            assert x["quantity"] == 2

    response = client.patch(
        f"/cdr/users/{cdr_admin.id}/purchases/{variant.id}/validated/?validated=True",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

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


def test_get_signatures_by_user_id():
    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]

    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]

    response = client.get(
        f"/cdr/users/{cdr_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_get_signatures_by_user_id_by_seller_id():
    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]

    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) in [x["document_id"] for x in response.json()]

    response = client.get(
        f"/cdr/sellers/{online_seller.id}/users/{cdr_user.id}/signatures/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]

    response = client.get(
        f"/cdr/sellers/{seller.id}/users/{cdr_bde.id}/signatures/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(signature.document_id) not in [x["document_id"] for x in response.json()]


def test_create_delete_signature():
    response = client.patch(
        "/cdr/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.patch(
        "/cdr/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.post(
        f"/cdr/users/{cdr_admin.id}/signatures/{document.id}/",
        json={
            "signature_type": DocumentSignatureType.material,
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 201

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
    assert str(document.id) in [x["document_id"] for x in response.json()]

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


def test_get_curriculums():
    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum.id) in [x["id"] for x in response.json()]


def test_create_delete_curriculum():
    response = client.post(
        "/cdr/curriculums/",
        json={
            "name": "Cursus crée",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201

    curriculum_id = uuid.UUID(response.json()["id"])

    response = client.post(
        "/cdr/curriculums/",
        json={
            "name": "Cursus crée",
        },
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(curriculum_id) in [x["id"] for x in response.json()]

    response = client.delete(
        f"/cdr/curriculums/{curriculum_id}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/cdr/curriculums/{curriculum_id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        "/cdr/curriculums/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(curriculum_id) not in [x["id"] for x in response.json()]


def test_create_delete_curriculum_membership():
    response = client.post(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 201

    response = client.delete(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 204

    response = client.post(
        f"/cdr/users/{cdr_user.id!s}/curriculums/{curriculum.id!s}/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 403


def test_get_payments_by_user_id():
    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 200
    assert str(payment.id) in [x["id"] for x in response.json()]

    response = client.get(
        f"/cdr/users/{cdr_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_bde.id}/payments/",
        headers={"Authorization": f"Bearer {token_bde}"},
    )
    assert response.status_code == 200
    assert str(payment.id) not in [x["id"] for x in response.json()]


def test_create_delete_payment():
    response = client.patch(
        "/cdr/status/",
        json={"status": "online"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    response = client.patch(
        "/cdr/status/",
        json={"status": "onsite"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )

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

    response = client.post(
        f"/cdr/users/{cdr_admin.id}/payments/",
        json={
            "total": 12345,
            "payment_type": PaymentType.card,
        },
        headers={"Authorization": f"Bearer {token_user}"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment_id) in [x["id"] for x in response.json()]

    response = client.delete(
        f"/cdr/users/{cdr_user.id}/payments/{payment_id}/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/cdr/users/{cdr_user.id}/payments/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    assert str(payment_id) not in [x["id"] for x in response.json()]

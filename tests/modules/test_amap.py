import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.amap import models_amap
from app.modules.amap.types_amap import AmapSlotType, DeliveryStatusType
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

amap_user: models_users.CoreUser
student_user: models_users.CoreUser
product: models_amap.Product
deletable_product: models_amap.Product
delivery: models_amap.Delivery
deletable_delivery: models_amap.Delivery
locked_delivery: models_amap.Delivery
order: models_amap.Order
deletable_order_by_admin: models_amap.Order


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global \
        amap_user, \
        student_user, \
        product, \
        deletable_product, \
        delivery, \
        deletable_delivery, \
        locked_delivery, \
        order, \
        deletable_order_by_admin

    amap_user = await create_user_with_groups([GroupType.amap])
    student_user = await create_user_with_groups(
        [],
    )

    product = models_amap.Product(
        id=str(uuid.uuid4()),
        name="Tomato",
        price=150,
        category="Test",
    )
    await add_object_to_db(product)
    deletable_product = models_amap.Product(
        id=str(uuid.uuid4()),
        name="Deletable Tomato",
        price=150,
        category="Test",
    )
    await add_object_to_db(deletable_product)

    delivery = models_amap.Delivery(
        id=str(uuid.uuid4()),
        delivery_date=datetime(2022, 8, 15, tzinfo=UTC),
        status=DeliveryStatusType.creation,
        name="Livraison 1",
    )
    await add_object_to_db(delivery)
    deletable_delivery = models_amap.Delivery(
        id=str(uuid.uuid4()),
        delivery_date=datetime(2022, 8, 16, tzinfo=UTC),
        status=DeliveryStatusType.creation,
        name="Livraison supprimable",
    )
    await add_object_to_db(deletable_delivery)

    locked_delivery = models_amap.Delivery(
        id=str(uuid.uuid4()),
        delivery_date=datetime(2022, 8, 17, tzinfo=UTC),
        status=DeliveryStatusType.locked,
        name="Livraison verrouillée",
    )
    await add_object_to_db(locked_delivery)

    order = models_amap.Order(
        order_id=str(uuid.uuid4()),
        user_id=student_user.id,
        delivery_id=delivery.id,
        amount=0,
        collection_slot=AmapSlotType.midi,
        ordering_date=datetime(2022, 8, 10, 12, 16, 26, tzinfo=UTC),
    )
    await add_object_to_db(order)

    deletable_order_by_admin = models_amap.Order(
        order_id=str(uuid.uuid4()),
        user_id=student_user.id,
        delivery_id=locked_delivery.id,
        amount=0,
        collection_slot=AmapSlotType.midi,
        ordering_date=datetime(2022, 8, 18, 12, 16, 26, tzinfo=UTC),
    )
    await add_object_to_db(deletable_order_by_admin)

    cash = models_amap.Cash(
        user_id=student_user.id,
        balance=666,
        last_order_date=datetime.now(UTC),
    )
    await add_object_to_db(cash)


def test_get_products(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.get(
        "/amap/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_product(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.post(
        "/amap/products",
        json={"name": "test", "price": 10, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_product_by_id(client: TestClient) -> None:
    # The user doesn't need to be part of group amap to get a product
    student_token = create_api_access_token(student_user)

    response = client.get(
        f"/amap/products/{product.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200


def test_edit_product(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.patch(
        f"/amap/products/{product.id}",
        json={"name": "testupdate", "price": 10, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_product(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/products/{deletable_product.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_deliveries(client: TestClient) -> None:
    # The user don't need to be part of group amap to get a delivery
    student_token = create_api_access_token(student_user)

    response = client.get(
        "/amap/deliveries",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200


def test_create_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.post(
        "/amap/deliveries",
        json={
            "name": "Livraison",
            "delivery_date": "2022-08-18",
            "products_ids": [product.id],
            "locked": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_delete_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/deliveries/{deletable_delivery.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_edit_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.patch(
        f"/amap/deliveries/{delivery.id}",
        json={
            "name": "Livraison editee",
            "delivery_date": "2022-08-18",
            "locked": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_add_product_to_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.post(
        f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_remove_product_from_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)
    response = client.request(
        method="DELETE",
        url=f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id, "notaproduct"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Recreate product for future tests
    response = client.post(
        f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_orders_from_delivery(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.get(
        f"/amap/deliveries/{delivery.id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_order_by_id(client: TestClient) -> None:
    token = create_api_access_token(amap_user)
    response = client.get(
        f"/amap/orders/{order.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_make_delivery_orderable(client: TestClient) -> None:
    token = create_api_access_token(amap_user)
    response = client.post(
        f"/amap/deliveries/{delivery.id}/openordering",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_add_order_to_delivery(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.post(
        "/amap/orders",
        json={
            "user_id": student_user.id,
            "delivery_id": delivery.id,
            "products_ids": [product.id],
            "collection_slot": "midi",
            "delivery_date": "2022-08-16",
            "products_quantity": [1],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201


def test_edit_order(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.patch(
        f"/amap/orders/{order.order_id}",
        json={
            "user_id": student_user.id,
            "delivery_id": delivery.id,
            "products_ids": [],
            "collection_slot": "soir",
            "delivery_date": "2022-08-16",
            "products_quantity": [],
            "order_id": order.order_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_remove_order(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.delete(
        f"/amap/orders/{order.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_remove_order_by_admin(client: TestClient) -> None:
    token = create_api_access_token(student_user)
    token_amap = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/orders/{deletable_order_by_admin.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400

    response = client.delete(
        f"/amap/orders/{deletable_order_by_admin.order_id}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 204


def test_get_users_cash(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.get(
        "/amap/users/cash",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_cash_by_id(client: TestClient) -> None:
    amap_token = create_api_access_token(amap_user)
    student_token = create_api_access_token(student_user)

    # The student user who is not part of AMAP group
    # should be able to access its own cash
    response = client.get(
        f"/amap/users/{student_user.id}/cash",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200

    # The student user who is not part of AMAP group
    # should not be able to access an other user cash
    response = client.get(
        f"/amap/users/{amap_user.id}/cash",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403

    # The AMAP user should be able to access an other user cash
    response = client.get(
        f"/amap/users/{student_user.id}/cash",
        headers={"Authorization": f"Bearer {amap_token}"},
    )
    assert response.status_code == 200


def test_create_cash_of_user(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.post(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 50, "user_id": amap_user.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_cash_by_id(client: TestClient) -> None:
    token = create_api_access_token(amap_user)

    response = client.post(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 50, "user_id": amap_user.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.patch(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 45},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_orders_of_user(client: TestClient) -> None:
    token = create_api_access_token(student_user)

    response = client.get(
        f"/amap/users/{student_user.id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

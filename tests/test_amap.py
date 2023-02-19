import uuid
from datetime import datetime

from app.dependencies import get_redis_client, get_settings
from app.main import app
from app.models import models_amap, models_core
from app.utils.types.amap_types import AmapSlotType, DeliveryStatusType
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

amap_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None
product: models_amap.Product | None = None
deletable_product: models_amap.Product | None = None
delivery: models_amap.Delivery | None = None
deletable_delivery: models_amap.Delivery | None = None
order: models_amap.Order | None = None

settings = app.dependency_overrides.get(get_settings, get_settings)()


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global amap_user, student_user, product, deletable_product, delivery, deletable_delivery, order, cash

    async with TestingSessionLocal() as db:
        amap_user = await create_user_with_groups([GroupType.amap], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        product = models_amap.Product(
            id=str(uuid.uuid4()), name="Tomato", price=1.5, category="Test"
        )
        db.add(product)
        deletable_product = models_amap.Product(
            id=str(uuid.uuid4()), name="Deletable Tomato", price=1.5, category="Test"
        )
        db.add(deletable_product)

        # We can not create two deliveries with the same date
        delivery = models_amap.Delivery(
            id=str(uuid.uuid4()),
            delivery_date=datetime(2022, 8, 15),
            status=DeliveryStatusType.creation,
        )
        db.add(delivery)
        deletable_delivery = models_amap.Delivery(
            id=str(uuid.uuid4()),
            delivery_date=datetime(2022, 8, 16),
            status=DeliveryStatusType.creation,
        )
        db.add(deletable_delivery)

        order = models_amap.Order(
            order_id=str(uuid.uuid4()),
            user_id=student_user.id,
            delivery_id=delivery.id,
            amount=0.0,
            collection_slot=AmapSlotType.midi,
            ordering_date=datetime(2022, 8, 10, 12, 16, 26),
            delivery_date=delivery.delivery_date,
        )
        db.add(order)
        await db.commit()

        cash = models_amap.Cash(user_id=student_user.id, balance=666)
        db.add(cash)
        await db.commit()


def test_get_products():
    token = create_api_access_token(amap_user)

    response = client.get(
        "/amap/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_create_product():
    token = create_api_access_token(amap_user)

    response = client.post(
        "/amap/products",
        json={"name": "test", "price": 0.1, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_get_product_by_id():
    # The user doesn't need to be part of group amap to get a product
    student_token = create_api_access_token(student_user)

    response = client.get(
        f"/amap/products/{product.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200


def test_edit_product():
    token = create_api_access_token(amap_user)

    response = client.patch(
        f"/amap/products/{product.id}",
        json={"name": "testupdate", "price": 0.1, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_delete_product():
    token = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/products/{deletable_product.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_deliveries():
    # The user don't need to be part of group amap to get a product
    student_token = create_api_access_token(student_user)

    response = client.get(
        "/amap/deliveries",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200


def test_create_delivery():
    token = create_api_access_token(amap_user)

    response = client.post(
        "/amap/deliveries",
        json={
            "delivery_date": "2022-08-17",
            "products_ids": [product.id],
            "locked": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_delete_delivery():
    token = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/deliveries/{deletable_delivery.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_edit_delivery():
    token = create_api_access_token(amap_user)

    response = client.patch(
        f"/amap/deliveries/{delivery.id}",
        json={"delivery_date": "2022-08-18", "locked": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_add_product_to_delivery():
    token = create_api_access_token(amap_user)

    response = client.post(
        f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_remove_product_from_delivery():
    token = create_api_access_token(amap_user)
    response = client.request(
        method="DELETE",
        url=f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id, "notaproduct"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_get_orders_from_delivery():
    token = create_api_access_token(amap_user)

    response = client.get(
        f"/amap/deliveries/{delivery.id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_order_by_id():
    token = create_api_access_token(amap_user)
    response = client.get(
        f"/amap/deliveries/{delivery.id}/orders/{order.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_make_delivery_orderable():
    token = create_api_access_token(amap_user)
    response = client.post(
        f"/amap/deliveries/{delivery.id}/openordering",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_add_order_to_delivery():
    # Enable Redis client for locker
    app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings, activate=True
    )

    token = create_api_access_token(student_user)

    response = client.post(
        f"/amap/deliveries/{delivery.id}/orders",
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

    # Disable Redis client (to avoid rate-limit)
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)

    assert response.status_code == 201


def test_edit_order():
    # Enable Redis client for locker
    app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings, activate=True
    )

    token = create_api_access_token(student_user)

    response = client.patch(
        f"/amap/deliveries/{delivery.id}/orders/{order.order_id}",
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

    # Disable Redis client (to avoid rate-limit)
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)

    assert response.status_code == 204


def test_remove_order():
    # Enable Redis client for locker
    app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings, activate=True
    )

    token = create_api_access_token(student_user)

    response = client.delete(
        f"/amap/deliveries/{delivery.id}/orders/{order.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Disable Redis client (to avoid rate-limit)
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)

    assert response.status_code == 204


def test_get_users_cash():
    token = create_api_access_token(amap_user)

    response = client.get(
        "/amap/users/cash",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_get_cash_by_id():
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


def test_create_cash_of_user():
    token = create_api_access_token(amap_user)

    response = client.post(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 50, "user_id": amap_user.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_edit_cash_by_id():
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


def test_get_orders_of_user():
    token = create_api_access_token(student_user)

    response = client.get(
        f"/amap/users/{student_user.id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

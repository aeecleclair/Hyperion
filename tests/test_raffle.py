import uuid
from datetime import datetime

from app.dependencies import get_redis_client, get_settings
from app.main import app
from app.models import models_core, models_raffle
from app.utils.types.groups_type import GroupType
from app.utils.types.raffle_types import RaffleStatusType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

raffle_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None
raffle: models_raffle.Raffle | None = None
typeticket: models_raffle.TypeTicket | None = None
lot: models_raffle.Lots | None = None
ticket: models_raffle.Tickets | None = None
cash: models_raffle.Cash | None = None


settings = app.dependency_overrides.get(get_settings, get_settings)()


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global raffle_user, student_user, raffle, typeticket, ticket, lot, cash

    async with TestingSessionLocal() as db:
        raffle_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        raffle = models_raffle.Raffle(
            id=str(uuid.uuid4()),
            name="The best raffle",
            status=RaffleStatusType.creation,
            group_id="123",
        )
        db.add(raffle)
        typeticket = models_raffle.Tickets(
            id=str(uuid.uuid4()), price=1.0, nb_ticket=1, raffle_id=raffle.id
        )
        db.add(typeticket)

        ticket = models_raffle.Tickets(
            id=str(uuid.uuid4()),
            raffle_id=raffle.id,
            type_id=typeticket.id,
            user_id=student_user.id,
        )
        db.add(ticket)

        lot = models_raffle.Lots(
            id=str(uuid.uuid4()),
            raffle_id=raffle.id,
            description="Description of the lot",
            name="Name of the lot",
            quantity=3,
        )
        db.add(lot)

        cash = models_raffle.Cash(
            user_id=student_user.id, user=student_user, balance=66
        )
        db.add(cash)

        await db.commit()


"""
def test_get_products():
    token = create_api_access_token(raffle_user)

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
            "delivery_date": "2022-08-18",
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

    # Recreate product for future tests
    response = client.post(
        f"/amap/deliveries/{delivery.id}/products",
        json={"products_ids": [product.id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


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
        f"/amap/orders/{order.order_id}",
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
        f"/amap/orders/{order.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Disable Redis client (to avoid rate-limit)
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)

    assert response.status_code == 204


def test_remove_order_by_admin():
    # Enable Redis client for locker
    app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings, activate=True
    )

    token = create_api_access_token(student_user)
    token_amap = create_api_access_token(amap_user)

    response = client.delete(
        f"/amap/orders/{deletable_order_by_admin.order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/amap/orders/{deletable_order_by_admin.order_id}",
        headers={"Authorization": f"Bearer {token_amap}"},
    )
    assert response.status_code == 204

    # Disable Redis client (to avoid rate-limit)
    app.dependency_overrides.get(get_redis_client, get_redis_client)(deactivate=True)


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
"""

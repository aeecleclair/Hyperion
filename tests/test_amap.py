from app.main import app
from app.models import models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

amap_user: models_core.CoreUser | None = None


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global amap_user
    async with TestingSessionLocal() as db:
        amap_user = await create_user_with_groups([GroupType.amap], db=db)
        await db.commit()


def test_get_rights():
    token = create_api_access_token(amap_user)
    response = client.get(
        "/amap/rights",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_amap():
    token = create_api_access_token(amap_user)

    response = client.post(
        "/amap/products",
        json={"name": "test", "price": 0.1, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    response = client.get(
        "/amap/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    id = response.json()[0]["id"]
    response = client.get(
        f"/amap/products/{id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/amap/products/{id}",
        json={"name": "testupdate", "price": 0.1, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.delete(
        f"/amap/products/{id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.post(
        "/amap/products",
        json={"name": "test", "price": 0.1, "category": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    prod_id = response.json()["id"]

    response = client.post(
        "/amap/deliveries",
        json={"delivery_date": "2022-08-15", "products_ids": [], "locked": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    id = response.json()["id"]

    response = client.get(
        "/amap/deliveries",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/amap/deliveries/{id}",
        json={"delivery_date": "2022-08-18", "id": id, "locked": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/amap/deliveries/{id}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.get(
        f"/amap/deliveries/{id}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.post(
        f"/amap/deliveries/{id}/products/{prod_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    response = client.delete(
        f"/amap/deliveries/{id}/products/{prod_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/amap/deliveries/{id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.post(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 50},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    response = client.get(
        "/amap/users/cash",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.get(
        f"/amap/users/{amap_user.id}/cash",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.patch(
        f"/amap/users/{amap_user.id}/cash",
        json={"balance": 45},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.post(
        f"/amap/deliveries/{id}/orders",
        json={
            "user_id": amap_user.id,
            "delivery_id": id,
            "products_ids": [],
            "collection_slot": "midi",
            "delivery_date": "2022-08-16",
            "products_quantity": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    order_id = response.json()["order_id"]

    response = client.patch(
        f"/amap/deliveries/{id}/orders",
        json={
            "user_id": amap_user.id,
            "delivery_id": id,
            "products_ids": [],
            "collection_slot": "soir",
            "delivery_date": "2022-08-16",
            "products_quantity": [],
            "order_id": order_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/amap/deliveries/{id}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.delete(
        f"/amap/deliveries/{id}/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    response = client.get(
        f"/amap/users/{amap_user.id}/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.delete(
        f"/amap/deliveries/{id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

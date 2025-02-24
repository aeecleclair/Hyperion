import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from tests.commons import (
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_users.CoreUser | None = None
admin_user_token: str = ""

FIREBASE_TOKEN_1 = "my-firebase-token"
FIREBASE_TOKEN_2 = "my-second-firebase-token"

TOPIC_1 = "cinema"
TOPIC_2 = "cinema_4c029b5f-2bf7-4b70-85d4-340a4bd28653"
TOPIC_3 = "cinema_2fa05a5b-43df-4ae6-8466-eeef649ac40e"
TOPIC_4 = "cinema_notsubscribed"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, admin_user_token
    admin_user = await create_user_with_groups([GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)


def test_register_firebase_device(client: TestClient) -> None:
    response = client.post(
        "/notification/devices",
        json={
            "firebase_token": FIREBASE_TOKEN_1,
        },
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_register_a_second_time_a_firebase_device(client: TestClient) -> None:
    # One user can and should register a device at least once a month
    response = client.post(
        "/notification/devices",
        json={
            "firebase_token": FIREBASE_TOKEN_1,
        },
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_register_second_firebase_device(client: TestClient) -> None:
    response = client.post(
        "/notification/devices",
        json={
            "firebase_token": FIREBASE_TOKEN_2,
        },
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_unregister_firebase_device(client: TestClient) -> None:
    response = client.delete(
        f"/notification/devices/{FIREBASE_TOKEN_2}",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_get_devices(client: TestClient) -> None:
    response = client.get(
        "/notification/devices/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    json = response.json()
    assert len(json) == 1
    assert json[0]["firebase_device_token"] == FIREBASE_TOKEN_1


def test_subscribe_to_topic(client: TestClient) -> None:
    response = client.post(
        f"/notification/topics/{TOPIC_1}/subscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204
    response = client.post(
        f"/notification/topics/{TOPIC_2}/subscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204
    response = client.post(
        f"/notification/topics/{TOPIC_3}/subscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_un_subscribe_to_topic(client: TestClient) -> None:
    response = client.post(
        f"/notification/topics/{TOPIC_3}/unsubscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_un_subscribe_to_topic_the_user_is_not_subscribed_to(
    client: TestClient,
) -> None:
    response = client.post(
        f"/notification/topics/{TOPIC_4}/unsubscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_get_topic(client: TestClient) -> None:
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    assert response.json() == [TOPIC_1]


def test_get_topic_identifier(client: TestClient) -> None:
    response = client.get(
        f"/notification/topics/{TOPIC_1}",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    assert response.json() == [TOPIC_2]

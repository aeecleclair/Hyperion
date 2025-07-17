import uuid

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.notification.models_notification import NotificationTopic
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_users.CoreUser | None = None
admin_user_token: str = ""

FIREBASE_TOKEN_1 = "my-firebase-token"
FIREBASE_TOKEN_2 = "my-second-firebase-token"

topic_1: NotificationTopic
topic_2: NotificationTopic
topic_3: NotificationTopic
topic_4: NotificationTopic


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, admin_user_token
    admin_user = await create_user_with_groups([GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)

    global topic_1, topic_2, topic_3, topic_4
    topic_1 = NotificationTopic(
        id=uuid.uuid4(),
        name="topic1",
        module_root="test",
        topic_identifier=None,
        restrict_to_group_id=None,
        restrict_to_members=False,
    )
    await add_object_to_db(topic_1)
    topic_2 = NotificationTopic(
        id=uuid.uuid4(),
        name="topic2",
        module_root="test",
        topic_identifier="4c029b5f-2bf7-4b70-85d4-340a4bd28653",
        restrict_to_group_id=None,
        restrict_to_members=False,
    )
    await add_object_to_db(topic_2)
    topic_3 = NotificationTopic(
        id=uuid.uuid4(),
        name="topic3",
        module_root="test",
        topic_identifier="2fa05a5b-43df-4ae6-8466-eeef649ac40e",
        restrict_to_group_id=None,
        restrict_to_members=False,
    )
    await add_object_to_db(topic_3)
    topic_4 = NotificationTopic(
        id=uuid.uuid4(),
        name="topic4",
        module_root="test",
        topic_identifier="notsubscribed",
        restrict_to_group_id=None,
        restrict_to_members=False,
    )
    await add_object_to_db(topic_4)


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


def test_get_topic(client: TestClient) -> None:
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 8


def test_subscribe_to_topic_without_identifier(client: TestClient) -> None:
    topic_id = str(topic_1.id)

    # Ensure that the user is not previously subscribed
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    topics = {topic["id"]: topic for topic in response.json()}
    assert topic_id in topics
    assert topics[topic_id]["is_user_subscribed"] is False

    response = client.post(
        f"/notification/topics/{topic_id}/subscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204

    # Ensure the user is now subscribed
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    topics = {topic["id"]: topic for topic in response.json()}
    assert topic_id in topics
    assert topics[topic_id]["is_user_subscribed"] is True


def test_subscribe_to_topic_with_identifier(client: TestClient) -> None:
    topic_id = str(topic_2.id)

    # Ensure that the user is not previously subscribed
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    topics = {topic["id"]: topic for topic in response.json()}
    assert topic_id in topics
    assert topics[topic_id]["is_user_subscribed"] is False

    response = client.post(
        f"/notification/topics/{topic_id}/subscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204

    # Ensure the user is now subscribed
    response = client.get(
        "/notification/topics/",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 200
    topics = {topic["id"]: topic for topic in response.json()}
    assert topic_id in topics
    assert topics[topic_id]["is_user_subscribed"] is True


def test_un_subscribe_to_topic(client: TestClient) -> None:
    response = client.post(
        f"/notification/topics/{topic_3.id}/unsubscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_un_subscribe_to_topic_the_user_is_not_subscribed_to(
    client: TestClient,
) -> None:
    response = client.post(
        f"/notification/topics/{topic_4.id}/unsubscribe",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_send_notification_to_group(client: TestClient) -> None:
    response = client.post(
        "/notification/send",
        json={
            "title": "Test Notification",
            "content": "This is a test notification.",
            "group_id": GroupType.admin.value,
        },
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_send_test_future_notification(client: TestClient) -> None:
    response = client.post(
        "/notification/test/send/future",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_send_test_notification_topic(client: TestClient) -> None:
    response = client.post(
        "/notification/test/send/topic",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204


def test_send_test_future_notification_topic(client: TestClient) -> None:
    response = client.post(
        "/notification/test/send/topic/future",
        headers={
            "Authorization": f"Bearer {admin_user_token}",
        },
    )
    assert response.status_code == 204

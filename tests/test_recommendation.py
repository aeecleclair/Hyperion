import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.modules.recommendation import models_recommendation
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

token_simple: str
token_BDE: str
recommendation: models_recommendation.Recommendation


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    user_simple = await create_user_with_groups(
        [],
    )

    global token_simple
    token_simple = create_api_access_token(user_simple)

    user_BDE = await create_user_with_groups([GroupType.BDE])

    global token_BDE
    token_BDE = create_api_access_token(user_BDE)

    global recommendation
    recommendation = models_recommendation.Recommendation(
        id=uuid.uuid4(),
        creation=datetime.now(UTC),
        title="Un titre",
        code="Un code",
        summary="Un résumé",
        description="Une description",
    )
    await add_object_to_db(recommendation)


def test_create_picture(client: TestClient) -> None:
    with Path("assets/images/default_recommendation.png").open("rb") as image:
        response = client.post(
            f"/recommendation/recommendations/{recommendation.id}/picture",
            files={"image": ("recommendation.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_BDE}"},
        )
    assert response.status_code == 201


def test_create_picture_for_non_existing_recommendation(client: TestClient) -> None:
    with Path("assets/images/default_recommendation.png").open("rb") as image:
        false_id = "be3017e8-ae8b-4488-a21a-41547c9cc846"
        response = client.post(
            f"/recommendation/recommendations/{false_id}/picture",
            files={"image": ("recommendation.png", image, "image/png")},
            headers={"Authorization": f"Bearer {token_BDE}"},
        )
    assert response.status_code == 404


def test_get_picture(client: TestClient) -> None:
    response = client.get(
        f"/recommendation/recommendations/{recommendation.id}/picture",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_recommendation(client: TestClient) -> None:
    response = client.get(
        "/recommendation/recommendations",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_recommendation(client: TestClient) -> None:
    response = client.post(
        "/recommendation/recommendations",
        json={
            "title": "Un titre",
            "code": "Un code",
            "summary": "Un résumé",
            "description": "Une description",
        },
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 201


def test_create_recommendation_with_no_body(client: TestClient) -> None:
    response = client.post(
        "/recommendation/recommendations",
        json={},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 422


def test_edit_recommendation(client: TestClient) -> None:
    response = client.patch(
        f"/recommendation/recommendations/{recommendation.id}",
        json={"title": "Nouveau titre"},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_edit_recommendation_with_no_body(client: TestClient) -> None:
    response = client.patch(
        f"/recommendation/recommendations/{recommendation.id}",
        json={},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_edit_for_non_existing_recommendation(client: TestClient) -> None:
    false_id = "098cdfb7-609a-493f-8d5a-47bbdba213da"
    response = client.patch(
        f"/recommendation/recommendations/{false_id}",
        json={"title": "Nouveau titre"},
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 404


def test_delete_recommendation(client: TestClient) -> None:
    response = client.delete(
        f"/recommendation/recommendations/{recommendation.id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 204


def test_delete_for_non_existing_recommendation(client: TestClient) -> None:
    false_id = "cfba17a6-58b8-4595-afb9-3c9e4e169a14"
    response = client.delete(
        f"/recommendation/recommendations/{false_id}",
        headers={"Authorization": f"Bearer {token_BDE}"},
    )
    assert response.status_code == 404

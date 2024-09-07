import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from tests.commons import (
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
student_user_to_delete: models_core.CoreUser
student_user_to_keep: models_core.CoreUser

token_admin_user: str
token_student_user: str


FABRISTPP_EMAIL_1 = "fabristpp.eclair1@etu.ec-lyon.fr"
FABRISTPP_EMAIL_2 = "fabristpp.eclair3@ecl21.ec-lyon.fr"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, student_user_to_delete, student_user_to_keep

    admin_user = await create_user_with_groups(
        [GroupType.admin],
    )
    student_user_to_keep = await create_user_with_groups(
        [GroupType.student, GroupType.BDE],
        email=FABRISTPP_EMAIL_1,
    )
    student_user_to_delete = await create_user_with_groups(
        [GroupType.student, GroupType.BDE, GroupType.CAA],
        email=FABRISTPP_EMAIL_2,
    )

    global token_admin_user, token_student_user
    token_admin_user = create_api_access_token(admin_user)
    token_student_user = create_api_access_token(student_user_to_keep)


def test_fusion_users(client: TestClient) -> None:
    response = client.patch(
        "/users/fusion",
        headers={"Authorization": f"Bearer {token_student_user}"},
        json={
            "user_kept_email": student_user_to_keep.email,
            "user_deleted_email": student_user_to_delete.email,
        },
    )
    assert response.status_code == 403

    response = client.patch(
        "/users/fusion",
        headers={"Authorization": f"Bearer {token_admin_user}"},
        json={
            "user_kept_email": student_user_to_keep.email,
            "user_deleted_email": student_user_to_delete.email,
        },
    )
    assert response.status_code == 204

    response = client.get(
        f"/users/{student_user_to_delete.id}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 404

    response = client.get(
        f"/users/{student_user_to_keep.id}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200

    response = client.get(
        f"/groups/{GroupType.CAA}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    users = response.json()["users"]
    users_ids = [user["id"] for user in users]
    assert student_user_to_keep.id in users_ids

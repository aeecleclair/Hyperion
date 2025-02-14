from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_users.CoreUser
student_user_to_delete: models_users.CoreUser
student_user_to_keep: models_users.CoreUser

token_admin_user: str
token_student_user: str

core_association_membership: models_core.CoreAssociationMembership

core_association_membership_user_del: models_core.CoreAssociationUserMembership
core_association_membership_user_kept: models_core.CoreAssociationUserMembership

FABRISTPP_EMAIL_1 = "fabristpp.eclair1@etu.ec-lyon.fr"
FABRISTPP_EMAIL_2 = "fabristpp.eclair3@ecl21.ec-lyon.fr"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, student_user_to_delete, student_user_to_keep

    admin_user = await create_user_with_groups(
        [GroupType.admin, GroupType.admin_cdr],
    )
    student_user_to_keep = await create_user_with_groups(
        [GroupType.BDE],
        email=FABRISTPP_EMAIL_1,
    )
    student_user_to_delete = await create_user_with_groups(
        [GroupType.BDE, GroupType.CAA],
        email=FABRISTPP_EMAIL_2,
    )

    global core_association_membership
    core_association_membership = models_core.CoreAssociationMembership(
        id=uuid4(),
        name="AEECL",
        group_id=GroupType.BDE,
    )
    await add_object_to_db(core_association_membership)

    global core_association_membership_user_del, core_association_membership_user_kept
    core_association_membership_user_del = models_core.CoreAssociationUserMembership(
        id=uuid4(),
        user_id=student_user_to_delete.id,
        association_membership_id=core_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=365),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=365),
    )
    await add_object_to_db(core_association_membership_user_del)
    core_association_membership_user_kept = models_core.CoreAssociationUserMembership(
        id=uuid4(),
        user_id=student_user_to_keep.id,
        association_membership_id=core_association_membership.id,
        start_date=datetime.now(tz=UTC).date() - timedelta(days=565),
        end_date=datetime.now(tz=UTC).date() + timedelta(days=465),
    )
    await add_object_to_db(core_association_membership_user_kept)

    global token_admin_user, token_student_user
    token_admin_user = create_api_access_token(admin_user)
    token_student_user = create_api_access_token(student_user_to_keep)


def test_fusion_users(client: TestClient) -> None:
    response = client.post(
        "/users/merge",
        headers={"Authorization": f"Bearer {token_student_user}"},
        json={
            "user_kept_email": student_user_to_keep.email,
            "user_deleted_email": student_user_to_delete.email,
        },
    )
    assert response.status_code == 403

    response = client.post(
        "/users/merge",
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
        f"/groups/{GroupType.CAA.value}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    users = response.json()["members"]
    users_ids = [user["id"] for user in users]
    assert student_user_to_keep.id in users_ids

    response = client.get(
        f"/memberships/users/{student_user_to_keep.id}",
        headers={"Authorization": f"Bearer {token_admin_user}"},
    )
    assert response.status_code == 200
    memberships = response.json()
    assert len(memberships) == 2
    user_kept_membership_aeecl_json = {
        "id": str(core_association_membership_user_kept.id),
        "user_id": str(student_user_to_keep.id),
        "membership_id": str(core_association_membership.id),
        "start_date": core_association_membership_user_kept.start_date.isoformat(),
        "end_date": core_association_membership_user_kept.end_date.isoformat(),
    }
    user_del_membership_aeecl_json = {
        "id": str(core_association_membership_user_del.id),
        "user_id": str(student_user_to_keep.id),
        "membership_id": str(core_association_membership.id),
        "start_date": core_association_membership_user_del.start_date.isoformat(),
        "end_date": core_association_membership_user_del.end_date.isoformat(),
    }
    assert user_kept_membership_aeecl_json in memberships
    assert user_del_membership_aeecl_json in memberships

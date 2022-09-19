import uuid

from app.main import app
from app.models import models_campaign, models_core
from app.utils.types.groups_type import GroupType
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None

section: models_campaign.Sections | None = None


@app.on_event("startup")  # create the datas needed in the tests
async def startuptest():
    global admin_user, student_user

    async with TestingSessionLocal() as db:
        admin_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        await db.commit()

    global section

    async with TestingSessionLocal() as db:
        section = models_campaign.Sections(
            id=str(uuid.uuid4()),
            name="BDE",
            description="Bureau Des Eleves",
            logo_path=".png",
        )
        db.add(section)
        await db.commit()


def test_get_sections():
    token = create_api_access_token(student_user)
    response = client.get(
        "/campaign/sections", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_add_sections():
    token = create_api_access_token(admin_user)
    response = client.post(
        "/campaign/sections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "ECLAIR",
            "description": "Association Informatique",
            "logo_path": "src",
        },
    )
    assert response.status_code == 201


def test_delete_section():
    token = create_api_access_token(admin_user)
    response = client.delete(
        f"/campaign/sections/{section.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

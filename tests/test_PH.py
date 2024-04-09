import datetime
import uuid
from pathlib import Path

import pytest_asyncio

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.ph import models_ph
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)

ph_user_ph: models_core.CoreUser
ph_user_simple: models_core.CoreUser
token_simple: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global ph_user_ph
    ph_user_ph = await create_user_with_groups([GroupType.ph])

    global token_ph
    token_ph = create_api_access_token(ph_user_ph)

    global ph_user_simple
    ph_user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(ph_user_simple)

    global paper
    paper = models_ph.Paper(
        id=str(uuid.uuid4()),
        name="OnlyPhans",
        release_date=datetime.datetime.fromisoformat("2024-10-22T00:00:00"),
    )
    await add_object_to_db(paper)


def test_create_paper():
    response = client.post(
        "/ph/",
        json={
            "id": str(uuid.uuid4()),
            "name": "Onlyphans test",
            "release_date": str(datetime.date(2024, 10, 21)),
        },
        headers={"Authorization": f"Bearer {token_ph}"},
    )
    assert response.status_code == 201


def test_get_papers():
    response = client.get(
        "/ph/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_paper_pdf():
    with Path("assets/pdf/default_PDF.pdf").open("rb") as pdf:
        response = client.post(
            f"/ph/{paper.id}/pdf",
            files={"pdf": ("test_paper.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {token_ph}"},
        )

    assert response.status_code == 201


def test_get_paper_pdf():
    response = client.get(
        f"/ph/{paper.id}/pdf",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_update_paper():
    response = client.patch(
        f"/ph/{paper.id}",
        json={
            "name": "OnlyPhans le 2",
            "release_date": str(datetime.date(2024, 1, 22)),
        },
        headers={"Authorization": f"Bearer {token_ph}"},
    )
    assert response.status_code == 204


def test_delete_paper():
    response = client.delete(
        f"/ph/{paper.id}",
        headers={"Authorization": f"Bearer {token_ph}"},
    )
    assert response.status_code == 204

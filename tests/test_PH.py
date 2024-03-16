import datetime
import uuid

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.modules.ph import models_ph
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global cinema_user_cinema
    ph_user_ph = await create_user_with_groups([GroupType.ph])

    global token_ph
    token_ph = create_api_access_token(ph_user_ph)

    global cinema_user_simple
    ph_user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(ph_user_simple)

    global paper
    paper = models_ph.Paper(
        id=str(uuid.uuid4()),
        name="Onlyphans",
        release_date=datetime.datetime.fromisoformat("2024-10-22T20:00:00"),
    )
    await add_object_to_db(paper)


def test_get_paper_pdf():
    response = client.get(
        f"/ph/{paper.id}/pdf",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_paper():
    response = client.post(
        "/ph/",
        json={
            "id": str(uuid.uuid4()),
            "name": "Onlyphans",
            "release_date": str(datetime.date(2024, 10, 22)),
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
    with open("assets/pdf/default_PDF.pdf", "rb") as pdf:
        response = client.post(
            f"/ph/{paper.id}/pdf",
            files={"pdf": ("test_paper.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {token_ph}"},
        )

    assert response.status_code == 201

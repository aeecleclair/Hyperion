import datetime
import uuid

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.modules.PH import models_PH
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
    PH_user_PH = await create_user_with_groups([GroupType.PH])

    global token_PH
    token_PH = create_api_access_token(PH_user_PH)

    global cinema_user_simple
    PH_user_simple = await create_user_with_groups([GroupType.student])

    global token_simple
    token_simple = create_api_access_token(PH_user_simple)

    global journal
    journal = models_PH.Journal(
        id=str(uuid.uuid4()),
        name="OnlyPhans",
        release_date=datetime.datetime.fromisoformat("2024-10-22T20:00:00"),
    )
    await add_object_to_db(journal)


def test_get_journal_pdf():
    response = client.get(
        f"/PH/{journal.id}/pdf",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_journal():
    response = client.post(
        "/PH/",
        json={
            "id": str(uuid.uuid4()),
            "name": "OnlyPhans",
            "release_date": str(datetime.date(2024, 10, 22)),
        },
        headers={"Authorization": f"Bearer {token_PH}"},
    )
    assert response.status_code == 201


def test_get_journals():
    response = client.get(
        "/PH/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_create_journal_pdf():
    with open("assets/pdf/default_PDF.pdf", "rb") as pdf:
        response = client.post(
            f"/PH/{journal.id}/pdf",
            files={"pdf": ("test_journal.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {token_PH}"},
        )

    assert response.status_code == 201

import datetime
import uuid
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import GroupType
from app.modules.ph import models_ph
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

ph_user_ph: models_core.CoreUser
ph_user_simple: models_core.CoreUser

token_ph: str
token_simple: str

paper: models_ph.Paper
paper2: models_ph.Paper


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global ph_user_ph
    ph_user_ph = await create_user_with_groups([GroupType.ph])

    global token_ph
    token_ph = create_api_access_token(ph_user_ph)

    global ph_user_simple
    ph_user_simple = await create_user_with_groups(
        [],
    )

    global token_simple
    token_simple = create_api_access_token(ph_user_simple)

    global paper
    paper = models_ph.Paper(
        id=uuid.uuid4(),
        name="OnlyPhans",
        release_date=datetime.date(2023, 10, 21),
    )
    await add_object_to_db(paper)

    global paper2
    paper2 = models_ph.Paper(
        id=uuid.uuid4(),
        name="OnlyPhans du futur",
        release_date=datetime.date(2090, 10, 21),
    )
    await add_object_to_db(paper2)


def test_create_paper(client: TestClient) -> None:
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


def test_get_papers(client: TestClient) -> None:
    response = client.get(
        "/ph/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(paper.id) in [response_paper["id"] for response_paper in response_json]
    assert str(paper2.id) not in [
        response_paper["id"] for response_paper in response_json
    ]


def test_get_papers_admin(client: TestClient) -> None:
    response = client.get(
        "/ph/admin",
        headers={"Authorization": f"Bearer {token_ph}"},
    )
    response_json = response.json()
    assert response.status_code == 200
    assert str(paper.id) in [response_paper["id"] for response_paper in response_json]
    assert str(paper2.id) in [response_paper["id"] for response_paper in response_json]


def test_create_paper_pdf_and_cover(client: TestClient) -> None:
    with Path("assets/pdf/default_ph.pdf").open("rb") as pdf:
        response = client.post(
            f"/ph/{paper.id}/pdf",
            files={"pdf": ("test_paper.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {token_ph}"},
        )

    assert response.status_code == 201
    assert Path(f"data/ph/pdf/{paper.id}.pdf").is_file()
    assert Path(f"data/ph/cover/{paper.id}.jpg").is_file()


def test_get_paper_pdf(client: TestClient) -> None:
    response = client.get(
        f"/ph/{paper.id}/pdf",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_get_cover(client: TestClient) -> None:
    response = client.get(
        f"/ph/{paper.id}/cover",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_update_paper(client: TestClient) -> None:
    response = client.patch(
        f"/ph/{paper.id}",
        json={
            "name": "OnlyPhans le 2",
            "release_date": str(datetime.date(2024, 1, 22)),
        },
        headers={"Authorization": f"Bearer {token_ph}"},
    )
    assert response.status_code == 204


def test_delete_paper(client: TestClient) -> None:
    with Path("assets/pdf/default_PDF.pdf").open("rb") as pdf:
        client.post(
            f"/ph/{paper.id}/pdf",
            files={"pdf": ("test_paper.pdf", pdf, "application/pdf")},
            headers={"Authorization": f"Bearer {token_ph}"},
        )

    assert Path(f"data/ph/pdf/{paper.id}.pdf").is_file()
    assert Path(f"data/ph/cover/{paper.id}.jpg").is_file()

    response = client.delete(
        f"/ph/{paper.id}",
        headers={"Authorization": f"Bearer {token_ph}"},
    )

    assert not Path(f"data/ph/pdf/{paper.id}.pdf").is_file()
    assert not Path(f"data/ph/cover/{paper.id}.jpg").is_file()
    assert response.status_code == 204

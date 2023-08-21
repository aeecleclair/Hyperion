import pytest_asyncio

from app.models import models_core
from app.utils.types.groups_type import GroupType

# We need to import event_loop for pytest-asyncio routine defined bellow
from tests.commons import event_loop  # noqa
from tests.commons import (
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

simple_user: models_core.CoreUser | None = None
admin_user: models_core.CoreUser | None = None
token_simple: str = ""
token_admin: str = ""
root = "root"
group_id = "random id"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global admin_user
    admin_user = await create_user_with_groups([GroupType.admin])
    global token_admin
    token_admin = create_api_access_token(admin_user)
    user_simple = await create_user_with_groups([GroupType.AE])
    global token_simple
    token_simple = create_api_access_token(user_simple)
    module_visibility = models_core.ModuleVisibility(
        root=root, allowed_group_id=group_id
    )
    await add_object_to_db(module_visibility)


def test_get_module_visibility():
    response = client.get(
        "/module-visibility",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_my_module_visibility():
    response = client.get(
        "/module-visibility/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_add_module_visibility():
    response = client.post(
        "/module-visibility/",
        json={
            "root": "root",
            "allowed_group_id": GroupType.AE.value,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_delete_loaners():
    response = client.delete(
        f"/module-visibility/{root}/{group_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_get_information():
    response = client.get(
        "/information",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_get_privacy():
    response = client.get(
        "/privacy",
    )
    assert response.status_code == 200


def test_get_terms_and_conditions():
    response = client.get(
        "/terms-and-conditions",
    )
    assert response.status_code == 200


def test_get_support():
    response = client.get(
        "/support",
    )
    assert response.status_code == 200


def test_get_security_txt():
    response = client.get(
        "/security.txt",
    )
    assert response.status_code == 200


def test_get_wellknown_security_txt():
    response = client.get(
        "/.well-known/security.txt",
    )
    assert response.status_code == 200


def test_get_stylesheet():
    response = client.get(
        "/style/connexion.css",
    )
    assert response.status_code == 200

    # This request should return a 404 as the stylesheet does not exist
    response = client.get(
        "/style/dontexist.css",
    )
    assert response.status_code == 404


def test_get_favicon():
    response = client.get(
        "/favicon.ico",
    )
    assert response.status_code == 200


def test_cors_authorized_origin():
    origin = "https://test-authorized-origin.com"
    headers = {
        "Access-Control-Request-Method": "GET",
        "origin": origin,
    }
    response = client.get("/information", headers=headers)
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_unauthorized_origin():
    origin = "https://test-UNauthorized-origin.com"
    headers = {
        "Access-Control-Request-Method": "GET",
        "origin": origin,
    }
    response = client.get("/information", headers=headers)
    # The origin should not be in the response as it is not authorized. We will check `None != origin`
    assert response.headers.get("access-control-allow-origin", None) != origin

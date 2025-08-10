import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

simple_user: models_users.CoreUser
admin_user: models_users.CoreUser
token_simple: str
token_admin: str
root = "root"
group_id = "random id"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user
    admin_user = await create_user_with_groups([GroupType.admin])
    global token_admin
    token_admin = create_api_access_token(admin_user)
    user_simple = await create_user_with_groups([GroupType.AE])
    global token_simple
    token_simple = create_api_access_token(user_simple)
    module_visibility = models_core.ModuleGroupVisibility(
        root=root,
        allowed_group_id=group_id,
    )
    await add_object_to_db(module_visibility)


def test_get_module_visibility(client: TestClient) -> None:
    response = client.get(
        "/module-visibility",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200


def test_get_my_module_visibility(client: TestClient) -> None:
    response = client.get(
        "/module-visibility/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


def test_add_group_module_visibility(client: TestClient) -> None:
    response = client.post(
        "/module-visibility/",
        json={
            "root": "root",
            "allowed_group_id": GroupType.AE.value,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_delete_group_visibility(client: TestClient) -> None:
    response = client.delete(
        f"/module-visibility/{root}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_add_account_type_module_visibility(client: TestClient) -> None:
    response = client.post(
        "/module-visibility/",
        json={
            "root": "root",
            "allowed_account_type": AccountType.demo.value,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201


def test_delete_account_type_visibility(client: TestClient) -> None:
    response = client.delete(
        f"/module-visibility/{root}/account-types/{AccountType.demo.value}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204


def test_get_information(client: TestClient) -> None:
    response = client.get(
        "/information",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_get_privacy(client: TestClient) -> None:
    response = client.get(
        "/privacy",
    )
    assert response.status_code == 200


def test_get_terms_and_conditions(client: TestClient) -> None:
    response = client.get(
        "/terms-and-conditions",
    )
    assert response.status_code == 200


def test_get_myeclpay_tos(client: TestClient) -> None:
    response = client.get(
        "/myeclpay-terms-of-service",
    )
    assert response.status_code == 200


def test_get_support(client: TestClient) -> None:
    response = client.get(
        "/support",
    )
    assert response.status_code == 200


def test_get_security_txt(client: TestClient) -> None:
    response = client.get(
        "/security.txt",
    )
    assert response.status_code == 200


def test_get_wellknown_security_txt(client: TestClient) -> None:
    response = client.get(
        "/.well-known/security.txt",
    )
    assert response.status_code == 200


def test_get_favicon(client: TestClient) -> None:
    response = client.get(
        "/favicon.ico",
    )
    assert response.status_code == 200


def test_cors_authorized_origin(client: TestClient) -> None:
    origin = "https://test-authorized-origin.com"
    headers = {
        "Access-Control-Request-Method": "GET",
        "origin": origin,
    }
    response = client.get("/information", headers=headers)
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_unauthorized_origin(client: TestClient) -> None:
    origin = "https://test-UNauthorized-origin.com"
    headers = {
        "Access-Control-Request-Method": "GET",
        "origin": origin,
    }
    response = client.get("/information", headers=headers)
    # The origin should not be in the response as it is not authorized. We will check `None != origin`
    assert response.headers.get("access-control-allow-origin", None) != origin

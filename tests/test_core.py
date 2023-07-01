from tests.commons import client


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

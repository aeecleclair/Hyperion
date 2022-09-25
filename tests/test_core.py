from tests.commons import client


def test_get_information():

    response = client.get(
        "/information",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


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

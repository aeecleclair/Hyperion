from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_read_users():
    response = client.get("/users")
    assert response.status_code == 200
    assert response.json() == {"users": ["K2", "Tyshaud"]}

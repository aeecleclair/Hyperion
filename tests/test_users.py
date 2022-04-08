from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine

from app.database import Base
from app.main import app
from app.dependencies import get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # Connect to the database

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)  # Create a session for testing purposes and create a test client

Base.metadata.create_all(
    bind=engine
)  # Run the tests with the test client and override the get_db function to use the testing session


def override_get_db():
    """Override the get_db function to use the testing session"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)  # Run the tests


def test_create_user():
    response = client.post(
        "/users/",
        json={
            "password": "password",
            "name": "UserName",
            "firstname": "UserFirstName",
            "nickname": "Nickname",
            "birth": "01012000",
            "promo": "2021",
            "floor": "Adoma",
            "email": "eclair2@myecl.fr",
            "created_on": 1,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "eclair@myecl.fr"
    assert "id" in data


def test_read_users():
    # TODO
    pass


def test_edit_user():
    # TODO
    pass


def test_delete_user():
    # TODO
    pass

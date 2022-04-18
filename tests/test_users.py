# from re import S
import pytest
from sqlalchemy import select
from app.models import models_core
from app.core import security

from tests.commons import TestingSessionLocal
from tests.commons import client
from tests.commons import id_sthock, password_sthock


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


@pytest.mark.asyncio
async def test_create_user():
    """Test the /users/create endpoint"""

    # First test with invalid email address
    response = client.post(
        "/users/create",
        json={
            "email": "user@example.fr",
            "account_type": "39691052-2ae5-4e12-99d0-7a9f5f2b0136",
        },
    )
    assert response.status_code == 400

    # Second test with valid email address and another type of account (staff instead of student)
    response = client.post(
        "/users/create",
        json={
            "email": "user@ecl21.ec-lyon.fr",
            "account_type": "703056c4-be9d-475c-aa51-b7fc62a96aaa",
        },
    )
    assert response.status_code == 201

    """Test the /users/activate endpoint"""
    # We first test if the activation works by itself
    token = (
        await TestingSessionLocal().execute(
            select(models_core.CoreUserUnconfirmed.activation_token).where(
                models_core.CoreUserUnconfirmed.email == "user@ecl21.ec-lyon.fr"
            )
        )
    ).fetchone()[0]

    response = client.post(
        "/users/activate",
        json={
            "activation_token": token,
            "name": "Debouck",
            "firstname": "Frank",
            "nickname": "Le Boss",
            "password": "MyPassword",
            "birthday": "2022-04-18",
            "phone": "0612345678",
            "floor": "Adomaxistr",
        },
    )
    assert response.status_code == 201

    """Check what happens if you try to create or activate an already existing user"""
    # What happend when you try to create an already activate user
    response = client.post(
        "/users/create",
        json={
            "email": "user@ecl21.ec-lyon.fr",
            "account_type": "703056c4-be9d-475c-aa51-b7fc62a96aaa",
        },
    )
    assert response.status_code == 422

    # Then we check that we can't activate the user twice (ie. the activation token is deleted affter creation)
    response = client.post(
        "/users/activate",
        json={
            "activation_token": token,
            "name": "Debouck",
            "firstname": "Frank",
            "nickname": "Le Boss",
            "password": "MyPassword",
            "birthday": "2022-04-18",
            "phone": "0612345678",
            "floor": "Adomaxistr",
        },
    )
    assert response.status_code == 422

    # TODO: Think about how to check that emails are sent correctly
    # TODO: make the test for the 403 error when trying to create another type of account being admin (wait for this to be done in user.py)

    # Then we check that we can't activate the user twice (ie. the activation token is deleted after activation)
    response = client.post(
        "/users/activate",
        json={
            "activation_token": token,
            "name": "Debouck",
            "firstname": "Frank",
            "nickname": "Le Boss",
            "password": "MyPassword",
            "birthday": "2022-04-18",
            "phone": "0612345678",
            "floor": "Adomaxistr",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password():
    """Test the /users/change-password endpoint"""
    new_password = "NewBigSecret"
    response = client.post(
        "/users/change-password",
        json={
            "user_id": id_sthock,
            "old_password": password_sthock,
            "new_password": new_password,
        },
    )
    new_hash_from_db = (
        await TestingSessionLocal().execute(
            select(models_core.CoreUser.password_hash).where(
                models_core.CoreUser.name == "Name"
            )
        )
    ).fetchone()[0]
    assert response.status_code == 201
    assert new_hash_from_db == security.get_password_hash(new_password)


def test_reset_password():
    """Test the procedure to reset a password"""
    pass

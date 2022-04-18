# from re import S
from tests.commons import client


def test_create_rows():  # A first test is needed to run startuptest once and create the datas needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass


def test_create_user():
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

    # TODO: make the test for the 403 error when trying to create another type of account being admin

    # TODO: add the function creating a user entirely on top of this file, so that we can be sure it is impossible
    # to create 2 users with the same address
    # Think about how to get the activation token to then activate the account


def test_activate_user():
    assert 1 == 1

"""This file should be the first one to be run (so the name should remain this way),
it triggers the "startup events" in all other test files"""
from tests.commons import client


def test_create_rows():  # A first test is needed to run startuptest once and create the data needed for the actual tests
    with client:  # That syntax trigger the startup events in commons.py and all test files
        pass

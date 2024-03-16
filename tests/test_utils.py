import uuid

import pytest
from fastapi import UploadFile

from app.utils.tools import get_file_from_data, save_file_as_data


async def test_save_file():
    valid_uuid = str(uuid.uuid4())
    with open("assets/images/default_profile_picture.png", "rb") as file:
        await save_file_as_data(
            image=UploadFile(file, headers={"content-type": "image/png"}),
            directory="test",
            filename=valid_uuid,
            request_id="request_id",
        )


async def test_save_file_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with pytest.raises(ValueError):
        with open("assets/images/default_profile_picture.png", "rb") as file:
            await save_file_as_data(
                image=UploadFile(file),
                directory="test",
                filename=not_a_uuid,
                request_id="request_id",
            )


def test_get_file_with_valid_uuid():
    valid_uuid = str(uuid.uuid4())
    get_file_from_data(
        directory="directory",
        filename=valid_uuid,
        default_asset="assets/images/default_profile_picture.png",
    )


def test_get_file_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with pytest.raises(ValueError):
        get_file_from_data(
            directory="directory", filename=not_a_uuid, default_asset="default_asset"
        )

import uuid

import pytest

from app.utils.tools import get_file_from_data


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

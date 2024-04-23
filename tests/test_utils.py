import shutil
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    get_file_path_from_data,
    save_bytes_as_data,
    save_file_as_data,
    save_pdf_first_page_as_image,
)


async def test_save_file():
    valid_uuid = str(uuid.uuid4())
    with Path("assets/images/default_profile_picture.png").open("rb") as file:
        await save_file_as_data(
            upload_file=UploadFile(file, headers={"content-type": "image/png"}),
            directory="test",
            filename=valid_uuid,
            request_id="request_id",
        )


async def test_save_file_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with (
        pytest.raises(ValueError, match="The filename is not a valid UUID"),
        Path("assets/images/default_profile_picture.png").open("rb") as file,
    ):
        await save_file_as_data(
            upload_file=UploadFile(file),
            directory="test",
            filename=not_a_uuid,
            request_id="request_id",
        )


async def test_save_bytes():
    valid_uuid = str(uuid.uuid4())
    with Path("assets/images/default_profile_picture.png").open("rb") as file:
        await save_bytes_as_data(
            file_bytes=file.read(),
            directory="test",
            filename=valid_uuid,
            extension="png",
            request_id="request_id",
        )


async def test_save_bytes_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with (
        pytest.raises(ValueError, match="The filename is not a valid UUID"),
        Path("assets/images/default_profile_picture.png").open("rb") as file,
    ):
        await save_bytes_as_data(
            file_bytes=file.read(),
            directory="test",
            filename=not_a_uuid,
            extension="png",
            request_id="request_id",
        )


def test_get_existing_file_path_with_valid_uuid():
    valid_uuid = str(uuid.uuid4())
    default_asset = "assets/images/default_profile_picture.png"
    file_path = Path(f"data/test/{valid_uuid}.png")
    shutil.copy(
        default_asset,
        file_path,
    )
    returned_path = get_file_path_from_data(
        directory="test",
        filename=valid_uuid,
        default_asset=default_asset,
    )
    assert returned_path == file_path


def test_get_non_existing_file_path_with_valid_uuid_return_default_asset():
    valid_uuid = str(uuid.uuid4())
    path = get_file_path_from_data(
        directory="test",
        filename=valid_uuid,
        default_asset="assets/images/default_profile_picture.png",
    )
    assert path == Path("assets/images/default_profile_picture.png")


def test_get_file_path_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with pytest.raises(ValueError, match="The filename is not a valid UUID"):
        get_file_path_from_data(
            directory="test",
            filename=not_a_uuid,
            default_asset="default_asset",
        )


def test_get_file_with_valid_uuid():
    valid_uuid = str(uuid.uuid4())
    default_asset = "assets/images/default_profile_picture.png"
    file = get_file_from_data(
        directory="test",
        filename=valid_uuid,
        default_asset=default_asset,
    )
    assert file.path == Path(default_asset)


def test_get_file_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with pytest.raises(ValueError, match="The filename is not a valid UUID"):
        get_file_from_data(
            directory="test",
            filename=not_a_uuid,
            default_asset="default_asset",
        )


def test_delete_file_with_valid_uuid():
    valid_uuid = str(uuid.uuid4())
    default_asset = "assets/images/default_profile_picture.png"
    file_png_path = Path(f"data/test/{valid_uuid}.png")
    file_jpg_path = Path(f"data/test/{valid_uuid}.jpg")

    shutil.copy(
        default_asset,
        file_png_path,
    )
    shutil.copy(
        default_asset,
        file_jpg_path,
    )

    delete_file_from_data(
        directory="test",
        filename=valid_uuid,
    )
    assert not Path(file_png_path).is_file()
    assert not Path(file_jpg_path).is_file()


def test_delete_file_raise_a_value_error_if_filename_isnt_an_uuid():
    not_a_uuid = "not_a_uuid"
    with pytest.raises(ValueError, match="The filename is not a valid UUID"):
        delete_file_from_data(
            directory="test",
            filename=not_a_uuid,
        )


async def test_save_pdf_first_page_as_image():
    valid_uuid = str(uuid.uuid4())

    await save_pdf_first_page_as_image(
        input_pdf_directory="test/pdf",
        output_image_directory="test/image",
        filename=valid_uuid,
        default_pdf_path="assets/pdf/default_pdf.pdf",
        request_id="request_id",
    )
    assert Path(f"data/test/image/{valid_uuid}.jpg").is_file()

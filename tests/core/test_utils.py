import shutil
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.core.core_endpoints import models_core
from app.types.core_data import BaseCoreData
from app.types.exceptions import CoreDataNotFoundError, FileNameIsNotAnUUIDError
from app.utils.tools import (
    delete_file_from_data,
    get_core_data,
    get_file_from_data,
    get_file_path_from_data,
    save_bytes_as_data,
    save_file_as_data,
    save_pdf_first_page_as_image,
    set_core_data,
)
from tests.commons import (
    add_object_to_db,
    get_TestingSessionLocal,
)


class ExempleCoreData(BaseCoreData):
    name: str = "default"
    age: int = 18


class ExempleDefaultCoreData(BaseCoreData):
    name: str = "Default name"
    age: int = 18


class ExempleDefaultWithoutDefaultValuesCoreData(BaseCoreData):
    name: str
    age: int


class ExempleExistingCoreData(BaseCoreData):
    name: str = "default existing name"
    age: int = 18


core_data: models_core.CoreData


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global core_data

    core_data = models_core.CoreData(
        schema="ExempleCoreData",
        data='{"name": "Fabristpp", "age": 42}',
    )
    await add_object_to_db(core_data)

    core_data = models_core.CoreData(
        schema="ExempleExistingCoreData",
        data='{"name": "default name", "age": 18}',
    )
    await add_object_to_db(core_data)


async def test_save_file() -> None:
    valid_uuid = str(uuid.uuid4())
    with Path("assets/images/default_profile_picture.png").open("rb") as file:
        await save_file_as_data(
            upload_file=UploadFile(
                file,
                headers=Headers({"content-type": "image/png"}),
            ),
            directory="test",
            filename=valid_uuid,
        )


async def test_save_file_with_invalid_content_type() -> None:
    valid_uuid = str(uuid.uuid4())
    with (
        pytest.raises(HTTPException, match="400: Invalid file format, supported*"),
        Path("assets/images/default_profile_picture.png").open("rb") as file,
    ):
        await save_file_as_data(
            upload_file=UploadFile(
                file,
                headers=Headers({"content-type": "test/test"}),
            ),
            directory="test",
            filename=valid_uuid,
        )


async def test_save_file_raise_a_value_error_if_filename_isnt_an_uuid() -> None:
    not_a_uuid = "not_a_uuid"
    with (
        pytest.raises(
            FileNameIsNotAnUUIDError,
            match="The filename is not a valid UUID",
        ),
        Path("assets/images/default_profile_picture.png").open("rb") as file,
    ):
        await save_file_as_data(
            upload_file=UploadFile(file),
            directory="test",
            filename=not_a_uuid,
        )


async def test_save_bytes() -> None:
    valid_uuid = str(uuid.uuid4())
    with Path("assets/images/default_profile_picture.png").open("rb") as file:
        await save_bytes_as_data(
            file_bytes=file.read(),
            directory="test",
            filename=valid_uuid,
            extension="png",
        )


async def test_save_bytes_raise_a_value_error_if_filename_isnt_an_uuid() -> None:
    not_a_uuid = "not_a_uuid"
    with (
        pytest.raises(
            FileNameIsNotAnUUIDError,
            match="The filename is not a valid UUID",
        ),
        Path("assets/images/default_profile_picture.png").open("rb") as file,
    ):
        await save_bytes_as_data(
            file_bytes=file.read(),
            directory="test",
            filename=not_a_uuid,
            extension="png",
        )


def test_get_existing_file_path_with_valid_uuid() -> None:
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


def test_get_non_existing_file_path_with_valid_uuid_return_default_asset() -> None:
    valid_uuid = str(uuid.uuid4())
    path = get_file_path_from_data(
        directory="test",
        filename=valid_uuid,
        default_asset="assets/images/default_profile_picture.png",
    )
    assert path == Path("assets/images/default_profile_picture.png")


def test_get_file_path_raise_a_value_error_if_filename_isnt_an_uuid() -> None:
    not_a_uuid = "not_a_uuid"
    with pytest.raises(
        FileNameIsNotAnUUIDError,
        match="The filename is not a valid UUID",
    ):
        get_file_path_from_data(
            directory="test",
            filename=not_a_uuid,
            default_asset="default_asset",
        )


def test_get_file_with_valid_uuid() -> None:
    valid_uuid = str(uuid.uuid4())
    default_asset = "assets/images/default_profile_picture.png"
    file = get_file_from_data(
        directory="test",
        filename=valid_uuid,
        default_asset=default_asset,
    )
    assert file.path == Path(default_asset)


def test_get_file_raise_a_value_error_if_filename_isnt_an_uuid() -> None:
    not_a_uuid = "not_a_uuid"
    with pytest.raises(
        FileNameIsNotAnUUIDError,
        match="The filename is not a valid UUID",
    ):
        get_file_from_data(
            directory="test",
            filename=not_a_uuid,
            default_asset="default_asset",
        )


def test_delete_file_with_valid_uuid() -> None:
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


def test_delete_file_raise_a_value_error_if_filename_isnt_an_uuid() -> None:
    not_a_uuid = "not_a_uuid"
    with pytest.raises(
        FileNameIsNotAnUUIDError,
        match="The filename is not a valid UUID",
    ):
        delete_file_from_data(
            directory="test",
            filename=not_a_uuid,
        )


async def test_save_pdf_first_page_as_image() -> None:
    valid_uuid = str(uuid.uuid4())

    await save_pdf_first_page_as_image(
        input_pdf_directory="test/pdf",
        output_image_directory="test/image",
        filename=valid_uuid,
        default_pdf_path="assets/pdf/default_pdf.pdf",
    )
    assert Path(f"data/test/image/{valid_uuid}.jpg").is_file()


async def test_get_core_data() -> None:
    async with get_TestingSessionLocal()() as db:
        exemple_core_data = await get_core_data(core_data_class=ExempleCoreData, db=db)
        assert exemple_core_data.name == "Fabristpp"
        assert exemple_core_data.age == 42


async def test_get_default_core_data() -> None:
    async with get_TestingSessionLocal()() as db:
        default_core_data = await get_core_data(
            core_data_class=ExempleDefaultCoreData,
            db=db,
        )
        assert default_core_data.name == "Default name"
        assert default_core_data.age == 18


async def test_get_default_without_default_values_core_data():
    async with get_TestingSessionLocal()() as db:
        with pytest.raises(CoreDataNotFoundError):
            await get_core_data(
                core_data_class=ExempleDefaultWithoutDefaultValuesCoreData,
                db=db,
            )


async def test_replace_core_data() -> None:
    async with get_TestingSessionLocal()() as db:
        core_data = ExempleExistingCoreData(
            name="ECLAIR",
            age=42,
        )
        await set_core_data(core_data=core_data, db=db)

        new_core_data = await get_core_data(
            core_data_class=ExempleExistingCoreData,
            db=db,
        )
        assert new_core_data.name == "ECLAIR"
        assert new_core_data.age == 42

import logging
import os
import re
import secrets
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import aiofiles
import fitz
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from jellyfish import jaro_winkler_similarity
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cruds_core, models_core
from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.models_core import CoreUser
from app.core.users import cruds_users
from app.types import core_data
from app.types.content_type import ContentType
from app.types.exceptions import CoreDataNotFoundException

hyperion_error_logger = logging.getLogger("hyperion.error")

uuid_regex = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
)


def is_user_member_of_an_allowed_group(
    user: CoreUser,
    allowed_groups: list[GroupType] | list[str],
) -> bool:
    """
    Test if the provided user is a member of at least one group from `allowed_groups`.

    When required groups can only be determined at runtime a list of strings (group UUIDs) can be provided.
    This may be useful for modules that can be used multiple times like the loans module.
    NOTE: if the provided string does not match a valid group, the function will return False
    """
    # We can not directly test is group_id is in user.groups
    # As user.groups is a list of CoreGroup and group_id is an UUID
    for allowed_group in allowed_groups:
        for user_group in user.groups:
            if allowed_group == user_group.id:
                # We know the user is a member of at least one allowed group
                return True
    return False


def is_user_external(
    user: CoreUser,
):
    """
    Users that are not members won't be able to use all features
    """
    return user.external is True


def sort_user(
    query: str,
    users: Sequence[models_core.CoreUser],
    limit: int = 10,
) -> list[models_core.CoreUser]:
    """
    Search for users using Fuzzy String Matching

    `query` will be compared against `users` name, firstname and nickname.
    The size of the answer can be limited using `limit` parameter.

    Use Jellyfish library
    """

    # TODO: we may want to cache this object. Its generation may take some time if there is a big user base
    names = [f"{user.firstname} {user.name}" for user in users]
    nicknames = [user.nickname for user in users]
    scored: list[
        tuple[CoreUser, float, float, int]
    ] = [  # (user, name_score, nickname_score, index)
        (
            user,
            jaro_winkler_similarity(query, name),
            jaro_winkler_similarity(query, nickname) if nickname else 0,
            index,
        )
        for index, (user, name, nickname) in enumerate(
            zip(users, names, nicknames, strict=True),
        )
    ]

    results = []
    for _ in range(min(limit, len(scored))):
        maximum_name = max(scored, key=lambda r: r[1])
        maximum_nickname = max(scored, key=lambda r: r[2])
        if maximum_name[1] > maximum_nickname[1]:
            results.append(maximum_name)
            scored[maximum_name[3]] = (  # We don't want to use this user again
                maximum_name[0],
                -1,
                -1,
                maximum_name[3],
            )
        else:
            results.append(maximum_nickname)
            scored[maximum_nickname[3]] = (  # We don't want to use this user again
                maximum_nickname[0],
                -1,
                -1,
                maximum_nickname[3],
            )

    return [result[0] for result in results]


async def is_group_id_valid(group_id: str, db: AsyncSession) -> bool:
    """
    Test if the provided group_id is a valid group.

    The group may be
     - an account type
     - a group type
     - a group created at runtime and stored in the database
    """
    return await cruds_groups.get_group_by_id(db=db, group_id=group_id) is not None


async def is_user_id_valid(user_id: str, db: AsyncSession) -> bool:
    """
    Test if the provided user_id is a valid user.
    """
    return await cruds_users.get_user_by_id(db=db, user_id=user_id) is not None


async def save_file_as_data(
    upload_file: UploadFile,
    directory: str,
    filename: str,
    request_id: str,
    max_file_size: int = 1024 * 1024 * 2,  # 2 MB
    accepted_content_types: list[ContentType] | None = None,
):
    """
    Save an image or pdf file to the data folder.

    - The file will be saved in the `data` folder: "data/{directory}/{filename}.ext"
    - Maximum size is 2MB by default, it can be changed using `max_file_size` (in bytes) parameter.
    - `accepted_content_types` is a list of accepted content types. By default, all format are accepted.
        Use: `["image/jpeg", "image/png", "image/webp"]` to accept only images.
    - Filename should be an uuid.

    The file extension will be inferred from the provided content file.
    There should only be one file with the same filename, thus, saving a new file will remove the existing even if its extension was different.
    Currently, compatible extensions are defined in the enum `ContentType`

    An HTTP Exception will be raised if an error occurres.

    The filename should be a uuid.

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """
    if accepted_content_types is None:
        # Accept only images by default
        accepted_content_types = [
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
            ContentType.pdf,
        ]

    if not uuid_regex.match(filename):
        hyperion_error_logger.error(
            f"save_file_as_data: security issue, the filename is not a valid UUID: {filename}.",
        )
        raise ValueError("The filename is not a valid UUID")

    if upload_file.content_type not in accepted_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format, supported {accepted_content_types}",
        )

    # We need to go to the end of the file to be able to get the size of the file
    upload_file.file.seek(0, os.SEEK_END)
    # Use file.tell() to retrieve the cursor's current position
    file_size = upload_file.file.tell()  # Bytes
    if file_size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size is too big. Limit is {max_file_size/1024/1024} MB",
        )
    # We go back to the beginning of the file to save it on the disk
    await upload_file.seek(0)

    extension = ContentType(upload_file.content_type).name
    # Remove the existing file if any and create the new one

    # If the directory does not exist, we want to create it
    Path(f"data/{directory}/").mkdir(parents=True, exist_ok=True)

    try:
        for filePath in Path().glob(f"data/{directory}/{filename}.*"):
            filePath.unlink()

        async with aiofiles.open(
            f"data/{directory}/{filename}.{extension}",
            mode="wb",
        ) as buffer:
            # https://stackoverflow.com/questions/63580229/how-to-save-uploadfile-in-fastapi
            while content := await upload_file.read(1024):
                await buffer.write(content)

    except Exception as error:
        hyperion_error_logger.error(
            f"save_file_to_the_disk: could not save file to {filename}: {error} ({request_id})",
        )
        raise HTTPException(status_code=400, detail="Could not save file")


async def save_bytes_as_data(
    file_bytes: bytes,
    directory: str,
    filename: str,
    extension: str,
    request_id: str,
):
    """
    Save bytes in file in the data folder.

    - The file will be saved in the `data` folder: "data/{directory}/{filename}.{extension}"

    The filename should be a uuid.
    No verifications will be made about the content of the file, it is up to the caller to ensure the content is valid and safe.

    An HTTP Exception will be raised if an error occurres.

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """

    if not uuid_regex.match(filename):
        hyperion_error_logger.error(
            f"save_file_as_data: security issue, the filename is not a valid UUID: {filename}.",
        )
        raise ValueError("The filename is not a valid UUID")

    # If the directory does not exist, we want to create it
    Path(f"data/{directory}/").mkdir(parents=True, exist_ok=True)

    try:
        for filePath in Path().glob(f"data/{directory}/{filename}.*"):
            filePath.unlink()

        async with aiofiles.open(
            f"data/{directory}/{filename}.{extension}",
            mode="wb",
        ) as buffer:
            await buffer.write(file_bytes)

    except Exception as error:
        hyperion_error_logger.error(
            f"save_file_to_the_disk: could not save file to {filename}: {error} ({request_id})",
        )
        raise HTTPException(status_code=400, detail="Could not save file")


def get_file_path_from_data(
    directory: str,
    filename: str,
    default_asset: str,
) -> Path:
    """
    If there is a file with the provided filename in the data folder, return it. The file extension will be inferred from the provided content file.
    > "data/{directory}/{filename}.ext"
    Otherwise, return the default asset.

    The filename should be a uuid.

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """
    if not uuid_regex.match(filename):
        hyperion_error_logger.error(
            f"get_file_from_data: security issue, the filename is not a valid UUID: {filename}. This mean that the user input was not properly checked.",
        )
        raise ValueError("The filename is not a valid UUID")

    for filePath in Path().glob(f"data/{directory}/{filename}.*"):
        return filePath

    return Path(default_asset)


def get_file_from_data(
    directory: str,
    filename: str,
    default_asset: str,
) -> FileResponse:
    """
    If there is a file with the provided filename in the data folder, return it. The file extension will be inferred from the provided content file.
    > "data/{directory}/{filename}.ext"
    Otherwise, return the default asset.

    The filename should be a uuid.

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """
    path = get_file_path_from_data(directory, filename, default_asset)

    return FileResponse(path)


def delete_file_from_data(
    directory: str,
    filename: str,
):
    """
    Delete all files with the provided filename in the data folder.
    > "data/{directory}/{filename}.ext"

    The filename should be a uuid.

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """
    if not uuid_regex.match(filename):
        hyperion_error_logger.error(
            f"get_file_from_data: security issue, the filename is not a valid UUID: {filename}. This mean that the user input was not properly checked.",
        )
        raise ValueError("The filename is not a valid UUID")

    for filePath in Path().glob(f"data/{directory}/{filename}.*"):
        filePath.unlink()


async def save_pdf_first_page_as_image(
    input_pdf_directory: str,
    output_image_directory: str,
    filename: str,
    default_pdf_path: str,
    request_id: str,
    jpg_quality=95,
):
    """
    Open the pdf file "data/{input_pdf_directory}/{filename}.ext" and export its first page as a jpg image.
    The image will be saved in the `data` folder: "data/{output_image_directory}/{filename}.jpg"

    WARNING: **NEVER** trust user input when calling this function. Always check that parameters are valid.
    """

    pdf_file_path = get_file_path_from_data(
        input_pdf_directory,
        filename,
        default_pdf_path,
    )

    paper_pdf: fitz.Document
    with fitz.open(pdf_file_path) as paper_pdf:
        page: fitz.Page = paper_pdf.load_page(0)

        cover: fitz.Pixmap = page.get_pixmap()

        cover_bytes: bytes = cover.tobytes(
            output="jpeg",
            jpg_quality=jpg_quality,
        )

        await save_bytes_as_data(
            file_bytes=cover_bytes,
            directory=output_image_directory,
            filename=filename,
            extension="jpg",
            request_id=request_id,
        )


def get_display_name(
    firstname: str,
    name: str,
    nickname: str | None,
) -> str:
    if nickname:
        return f"{firstname} {name} ({nickname})"
    return f"{firstname} {name}"


def get_random_string(length: int = 5) -> str:
    return "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(length)
    )


CoreDataClass = TypeVar("CoreDataClass", bound=core_data.BaseCoreData)


async def get_core_data(
    core_data_class: type[CoreDataClass],
    db: AsyncSession,
) -> CoreDataClass:
    """
    Access the core data stored in the database, using the name of the class `core_data_class`.
    If the core data does not exist, it returns a new instance of `core_data_class`, including its default values, or raise a CoreDataNotFoundException.
    `core_data_class` should be a class extending `BaseCoreData`.

    This method should be called using the class object, and not an instance of the class:
    ```python
    await get_core_data(ExempleCoreData, db)
    ```

    See `BaseCoreData` for more information.
    """
    # `core_data_class` contains the class object, and not an instance of the class.
    # We can call `core_data_class.__name__` to get the name of the class
    schema_name = core_data_class.__name__
    core_data_model = await cruds_core.get_core_data_crud(
        schema=schema_name,
        db=db,
    )

    if core_data_model is None:
        # Return default values
        try:
            return core_data_class()
        except ValidationError as error:
            # If creating a new instance of the class raises a ValidationError, it means that the class does not have default values
            # We should then raise an exception
            raise CoreDataNotFoundException() from error

    return core_data_class.model_validate_json(
        core_data_model.data,
        strict=True,
    )


async def set_core_data(
    core_data: core_data.BaseCoreData,
    db: AsyncSession,
) -> None:
    """
    Set the core data in the database using the name of the class `core_data` is an instance of.

    This method should be called using an instance of a class extending `BaseCoreData`:
    ```python
    example_core_data = ExempleCoreData()
    await get_core_data(example_core_data, db)
    ```

    See `BaseCoreData` for more information.
    """
    # `core_data` contains an instance of the class.
    # We call `core_data_class.__class__.__name__` to get the name of the class
    schema_name = core_data.__class__.__name__

    core_data_model = models_core.CoreData(
        schema=schema_name,
        data=core_data.model_dump_json(),
    )

    # We want to remove the old data
    await cruds_core.delete_core_data_crud(schema=schema_name, db=db)
    # And then add the new one
    await cruds_core.add_core_data_crud(core_data=core_data_model, db=db)

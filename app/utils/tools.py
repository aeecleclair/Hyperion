import bisect
import logging
import os
import re
import secrets
import unicodedata
from collections.abc import Callable, Sequence
from inspect import iscoroutinefunction
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import aiofiles
import fitz
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from jellyfish import jaro_winkler_similarity
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import cruds_core, models_core
from app.core.groups import cruds_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import cruds_users, models_users
from app.core.users.models_users import CoreUser
from app.core.utils import security
from app.types import core_data
from app.types.content_type import ContentType
from app.types.exceptions import CoreDataNotFoundError, FileNameIsNotAnUUIDError
from app.utils.mail.mailworker import send_email

if TYPE_CHECKING:
    from app.core.utils.config import Settings


hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")


templates = Jinja2Templates(directory="assets/templates")


uuid_regex = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
)


def is_user_external(
    user: CoreUser,
):
    """
    Users that are not members won't be able to use all features
    """
    return user.account_type == AccountType.external


def sort_user(
    query: str,
    users: Sequence[models_users.CoreUser],
    limit: int = 10,
) -> list[models_users.CoreUser]:
    """
    Search for users using Fuzzy String Matching

    `query` will be compared against `users` name, firstname and nickname.
    Accents will be ignored.
    The size of the answer can be limited using `limit` parameter.

    Use Jaro-Winkler algorithm from Jellyfish library.
    """

    def unaccent(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf8")

    query = unaccent(query)
    scored: list[tuple[CoreUser, float]] = []
    for user in users:
        firstname = unaccent(user.firstname)
        name = unaccent(user.name)
        nickname = unaccent(user.nickname) if user.nickname else None
        score = max(
            jaro_winkler_similarity(query, firstname),
            jaro_winkler_similarity(query, name),
            jaro_winkler_similarity(query, f"{firstname} {name}"),
            jaro_winkler_similarity(query, f"{name} {firstname}"),
            jaro_winkler_similarity(query, nickname) if nickname else 0,
        )
        bisect.insort(scored, (user, score), key=(lambda s: s[1]))
        if len(scored) > limit:
            scored.pop(0)

    return [user for user, _ in reversed(scored)]


def is_user_member_of_any_group(
    user: models_users.CoreUser,
    allowed_groups: list[str] | list[GroupType],
) -> bool:
    """
    Check if the user is a member of the group.
    """
    user_groups_id = [group.id for group in user.groups]
    return any(group_id in user_groups_id for group_id in allowed_groups)


async def is_group_id_valid(group_id: str, db: AsyncSession) -> bool:
    """
    Test if the provided group_id is a valid group.

    The group may be
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
        raise FileNameIsNotAnUUIDError()

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
            detail=f"File size is too big. Limit is {max_file_size / 1024 / 1024} MB",
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

    except Exception:
        hyperion_error_logger.exception(
            f"save_file_to_the_disk: could not save file to {filename} ({request_id})",
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
        raise FileNameIsNotAnUUIDError()

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

    except Exception:
        hyperion_error_logger.exception(
            f"save_file_to_the_disk: could not save file to {filename} ({request_id})",
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
        raise FileNameIsNotAnUUIDError()

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
        raise FileNameIsNotAnUUIDError()

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
    If the core data does not exist, it returns a new instance of `core_data_class`, including its default values, or raise a CoreDataNotFoundError.
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
            raise CoreDataNotFoundError() from error

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


async def create_and_send_email_migration(
    user_id: str,
    new_email: str,
    old_email: str,
    make_user_external: bool,
    db: AsyncSession,
    settings: "Settings",
) -> None:
    """
    Create an email migration token, add it to the database and send an email to the user.

    You should always verify the email address before using this method:
     - you should verify that the email address is not already in use
     - you should check the email address format
     - you can choose if the user should become an external or a member user after the email change
    """
    confirmation_token = security.generate_token()

    migration_object = models_users.CoreUserEmailMigrationCode(
        user_id=user_id,
        new_email=new_email,
        old_email=old_email,
        confirmation_token=confirmation_token,
        make_user_external=make_user_external,
    )

    await cruds_users.create_email_migration_code(
        migration_object=migration_object,
        db=db,
    )

    if settings.SMTP_ACTIVE:
        migration_content = templates.get_template("migration_mail.html").render(
            {
                "migration_link": f"{settings.CLIENT_URL}users/migrate-mail-confirm?token={confirmation_token}",
            },
        )
        send_email(
            recipient=new_email,
            subject="MyECL - Confirm your new email address",
            content=migration_content,
            settings=settings,
        )
    else:
        hyperion_security_logger.info(
            f"You can confirm your new email address by clicking the following link: {settings.CLIENT_URL}users/migrate-mail-confirm?token={confirmation_token}",
        )


async def execute_async_or_sync_method(
    job_function: Callable[..., Any],
    **kwargs,
):
    """
    Execute the job_function with the provided kwargs, either as a coroutine or a regular function.
    """
    if iscoroutinefunction(job_function):
        return await job_function(**kwargs)
    return job_function(**kwargs)

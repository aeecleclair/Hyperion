import glob
import logging
import os
import shutil

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from rapidfuzz import process
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_groups, cruds_users
from app.models import models_core
from app.models.models_core import CoreUser
from app.utils.types.groups_type import GroupType

hyperion_error_logger = logging.getLogger("hyperion.error")


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


def fuzzy_search_user(
    query: str,
    users: list[models_core.CoreUser],
    limit: int = 10,
) -> list[models_core.CoreUser]:
    """
    Search for users using Fuzzy String Matching

    `query` will be compared against `users` name, firstname and nickname.
    The size of the answer can be limited using `limit` parameter.

    Use RapidFuzz library
    """

    # We can give a dictionary of {object: string used for the comparison} to the extract function
    # https://maxbachmann.github.io/RapidFuzz/Usage/process.html#extract

    # TODO: we may want to cache this object. Its generation may take some time if there is a big user base
    choices = {}

    for user in users:
        choices[user] = f"{user.firstname} {user.name} {user.nickname}"

    results: list[tuple[str, int | float, models_core.CoreUser]] = process.extract(
        query, choices, limit=limit
    )

    # results has the format : (string used for the comparison, similarity score, object)
    return [res[2] for res in results]


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
    image: UploadFile,
    directory: str,
    filename: str,
    request_id: str,
    max_file_size: int = 1024 * 1024 * 2,  # 2 MB
    accepted_content_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ],  # images only
):
    """
    Save an image file to the data folder.

    - The file will be saved in the `data` folder: "data/{directory}/{filename}.ext"
    - Maximum size is 2MB by default, it can be changed using `max_file_size` (in bytes) parameter.
    - `accepted_content_types` is a list of accepted content types. By default, only images are accepted.
        Use: `["image/jpeg", "image/png", "image/webp"]` to accept only images.

    The file extension will be inferred from the provided content file.
    There should only be one file with the same filename, thus, saving a new file will remove the existing even if its extension was different.
    Currently, compatible extensions are :
     - png
     - jpg
     - webp

    An HTTP Exception will be raised if an error occurres.
    """
    if image.content_type not in accepted_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format, supported {accepted_content_types}",
        )

    # We need to go to the end of the file to be able to get the size of the file
    image.file.seek(0, os.SEEK_END)
    # Use file.tell() to retrieve the cursor's current position
    file_size = image.file.tell()  # Bytes
    if file_size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size is too big. Limit is {max_file_size} MB",
        )
    # We go back to the beginning of the file to save it on the disk
    await image.seek(0)

    extensions_mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    extension = extensions_mapping.get(image.content_type, "")
    # Remove the existing file if any and create the new one
    try:
        for filePath in glob.glob(f"data/{directory}/{filename}.*"):
            os.remove(filePath)

        with open(f"data/{directory}/{filename}.{extension}", "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    except Exception as error:
        hyperion_error_logger.error(
            f"save_file_to_the_disk: could not save file to {filename}: {error} ({request_id})"
        )
        raise HTTPException(status_code=400, detail="Could not save file")


def get_file_from_data(
    directory: str,
    filename: str,
    default_asset: str,
):
    """
    If there is a file with the provided filename in the data folder, return it. The file extension will be inferred from the provided content file.
    > "data/{directory}/{filename}.ext"
    Otherwise, return the default asset.
    """
    for filePath in glob.glob(f"data/{directory}/{filename}.*"):
        return FileResponse(filePath)

    return FileResponse(default_asset)

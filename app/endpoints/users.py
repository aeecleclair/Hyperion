import logging
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta
from os.path import exists

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import Settings
from app.cruds import cruds_groups, cruds_users
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_core
from app.schemas import schemas_core
from app.utils.mail.mailworker import send_email
from app.utils.tools import fuzzy_search_user
from app.utils.types import standard_responses
from app.utils.types.groups_type import AccountType, GroupType
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")

templates = Jinja2Templates(directory="templates")


@router.get(
    "/users/",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
    tags=[Tags.users],
)
async def read_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all users from database as a list of `CoreUserSimple`

    **This endpoint is only usable by administrators**
    """

    users = await cruds_users.get_users(db)
    return users


@router.get(
    "/users/search",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
    tags=[Tags.users],
)
async def search_users(
    query: str,
    includedGroups: list[str] = [],
    excludedGroups: list[str] = [],
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Search for an user using Fuzzy String Matching

    `query` will be compared against users name, firstname and nickname

    **The user must be authenticated to use this endpoint**
    """

    users = await cruds_users.get_users(
        db, includedGroups=includedGroups, excludedGroups=excludedGroups
    )

    return fuzzy_search_user(query, users)


@router.get(
    "/users/me",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def read_current_user(
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return `CoreUser` representation of current user

    **The user must be authenticated to use this endpoint**
    """

    return user


@router.post(
    "/users/create",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_user_by_user(
    user_create: schemas_core.CoreUserCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Start the user account creation process. The user will be sent an email with a link to activate their account.
    > The received token needs to be send to `/users/activate` endpoint to activate the account.

    If the **password** is not provided, it will be required during the activation process. Don't submit a password if you are creating an account for someone else.

    When creating **student** or **staff** account a valid ECL email is required.
    Only admin users can create other **account types**, contact ÉCLAIR for more informations.
    """
    # Check the account type

    # For staff and student
    # ^[\w\-.]*@(ecl\d{2})|(alternance\d{4})?.ec-lyon.fr$
    # For staff
    # ^[\w\-.]*@ec-lyon.fr$
    # For student
    # ^[\w\-.]*@(ecl\d{2})|(alternance\d{4}).ec-lyon.fr$

    if re.match(r"^[a-zA-Z0-9_\-.]*@ec-lyon.fr", user_create.email):
        # Its a staff email address
        account_type = AccountType.staff
    elif re.match(
        r"^[\w\-.]*@(ecl\d{2})|(alternance\d{4}).ec-lyon.fr$", user_create.email
    ):
        # Its a student email address
        account_type = AccountType.student
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid ECL email address.",
        )

    # Make sure a confirmed account does not already exist
    db_user = await cruds_users.get_user_by_email(db=db, email=user_create.email)
    if db_user is not None:
        hyperion_security_logger.warning(
            f"Create_user: an user with email {user_create.email} already exist ({request_id})"
        )
        # We will send to the email a message explaining he already have an account and can reset their password if they want.
        if settings.SMTP_ACTIVE:
            background_tasks.add_task(
                send_email,
                recipient=user_create.email,
                subject="MyECL - your account already exist",
                content="This email address is already associated to an account. If you forget your credentials, you can reset your password [here]()",
                settings=settings,
            )

        # Fail silently: the user should not be informed that an user with the email address already exist.
        return standard_responses.Result(success=True)

    # There might be an unconfirmed user in the database but its not an issue. We will generate a second activation token.

    try:
        await create_user(
            email=user_create.email,
            password=user_create.password,
            account_type=account_type,
            background_tasks=background_tasks,
            db=db,
            settings=settings,
            request_id=request_id,
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))

    return standard_responses.Result(success=True)


@router.post(
    "/users/batch-creation",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def batch_create_users(
    user_creates: list[schemas_core.CoreBatchUserCreateRequest],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Batch user account creation process. All users will be sent an email with a link to activate their account.
    > The received token needs to be send to `/users/activate` endpoint to activate the account.

    Even for creating **student** or **staff** account a valid ECL email is not required but should preferably be used.

    The endpoint return a dictionary of unsuccessful user creation: `{email: error message}`.

    **This endpoint is only usable by administrators**
    """

    failed = {}

    for user_create in user_creates:
        try:
            await create_user(
                email=user_create.email,
                password=None,  # The administrator does not provide an email when creating an account for someone else
                account_type=user_create.account_type,
                background_tasks=background_tasks,
                db=db,
                settings=settings,
                request_id=request_id,
            )
        except Exception as error:
            failed[user_create.email] = error

    return standard_responses.BatchResult(failed=failed)


async def create_user(
    email: str,
    password: str | None,
    account_type: AccountType,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    settings: Settings,
    request_id: str,
) -> None:
    """
    User creation process. This function is used by both `/users/create` and `/users/admin/create` endpoints
    """
    # Warning: the validation token (and thus user_unconfirmed object) should **never** be returned in the request

    # If an account already exist, we can not create a new one
    db_user = await cruds_users.get_user_by_email(db=db, email=email)
    if db_user is not None:
        raise ValueError(f"An account with the email {email} already exist")
    # There might be an unconfirmed user in the database but its not an issue. We will generate a second activation token.

    if password is not None:
        password_hash = security.get_password_hash(password)
    else:
        password_hash = None
    activation_token = security.generate_token()

    # Add the unconfirmed user to the unconfirmed_user table

    user_unconfirmed = models_core.CoreUserUnconfirmed(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=password_hash,
        account_type=account_type,
        activation_token=activation_token,
        created_on=datetime.now(),
        expire_on=datetime.now()
        + timedelta(hours=settings.USER_ACTIVATION_TOKEN_EXPIRE_HOURS),
    )

    await cruds_users.create_unconfirmed_user(user_unconfirmed=user_unconfirmed, db=db)

    # After adding the unconfirmed user to the database, we got an activation token that need to be send by email,
    # in order to make sure the email address is valid

    if settings.SMTP_ACTIVE:
        background_tasks.add_task(
            send_email,
            recipient=email,
            subject="MyECL - confirm your email",
            content=f"Please confirm your MyECL account with the token {activation_token} : https://hyperion.myecl.fr/users/activate?activation_token={activation_token}",
            settings=settings,
        )
    hyperion_security_logger.info(
        f"Create_user: Creating an unconfirmed account for {email} with token {activation_token} ({request_id})"
    )


@router.get(
    "/users/activate",
    response_class=HTMLResponse,
    status_code=201,
    tags=[Tags.users],
)
async def get_user_activation_page(
    # request need to be passed to Jinja2 to generate the HTML page
    request: Request,
    activation_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return a HTML page to activate an account. The activation token is passed as a query string.

    **This endpoint is an UI endpoint which send and html page response.
    """
    print("Hello")

    unconfirmed_user = await cruds_users.get_unconfirmed_user_by_activation_token(
        db=db, activation_token=activation_token
    )
    if unconfirmed_user is None:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "The activation token is invalid",
            },
        )
    if unconfirmed_user.expire_on < datetime.now():
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "The activation token has expired",
            },
        )

    return templates.TemplateResponse(
        "activation.html",
        {
            "request": request,
            "activation_token": activation_token,
            "user_email": unconfirmed_user.email,
            "has_password": unconfirmed_user.password_hash is not None,
        },
    )


@router.post(
    "/users/activate",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def activate_user(
    user: schemas_core.CoreUserActivateRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """
    Activate the previously created account.

    **token**: the activation token send by email to the user

    **password**: user password, required if it was not provided previously
    """
    # We need to find the corresponding user_unconfirmed
    unconfirmed_user = await cruds_users.get_unconfirmed_user_by_activation_token(
        db=db, activation_token=user.activation_token
    )
    if unconfirmed_user is None:
        raise HTTPException(status_code=404, detail="Invalid activation token")

    # We need to make sure the unconfirmed user is still valid
    if unconfirmed_user.expire_on < datetime.now():
        raise HTTPException(status_code=400, detail="Expired activation token")

    # An account with the same email may exist if:
    # - the user called two times the user creation endpoints and got two activation token
    # - used a first token to activate its account
    # - tries to use the second one
    # Though usually all activation tokens linked to the email should have been deleted when the account was activated
    db_user = await cruds_users.get_user_by_email(db=db, email=unconfirmed_user.email)
    if db_user is not None:
        raise HTTPException(
            status_code=400,
            detail=f"The account with the email {unconfirmed_user.email} is already confirmed",
        )

    # If a password was provided in this request, we will use this one as it is more recent
    if user.password is not None:
        password_hash = security.get_password_hash(user.password)
    else:
        # No new password were provided, we need to make sure one was previously provided during the account creation process
        if unconfirmed_user.password_hash is not None:
            password_hash = unconfirmed_user.password_hash
        else:
            raise HTTPException(status_code=400, detail="A password was never provided")

    confirmed_user = models_core.CoreUser(
        id=unconfirmed_user.id,
        email=unconfirmed_user.email,
        password_hash=password_hash,
        name=user.name,
        firstname=user.firstname,
        nickname=user.nickname,
        birthday=user.birthday,
        promo=user.promo,
        phone=user.phone,
        floor=user.floor,
        created_on=datetime.now(),
    )
    # We add the new user to the database
    try:
        await cruds_users.create_user(db=db, user=confirmed_user)
        await cruds_groups.create_membership(
            db=db,
            membership=models_core.CoreMembership(
                group_id=unconfirmed_user.account_type,
                user_id=unconfirmed_user.id,
            ),
        )

        # We remove all unconfirmed users with the same email address
        await cruds_users.delete_unconfirmed_user_by_email(
            db=db, email=unconfirmed_user.email
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    hyperion_security_logger.info(
        f"Activate_user: Activated user {confirmed_user.id} ({request_id})"
    )
    return standard_responses.Result()


@router.post(
    "/users/make-admin",
    response_model=standard_responses.Result,
    status_code=200,
    tags=[Tags.users],
)
async def make_admin(
    db: AsyncSession = Depends(get_db),
):
    """
    This endpoint is only usable if the database contains exactly one user.
    It will add this user to the `admin` group.
    """
    users = await cruds_users.get_users(db=db)

    if len(users) != 1:
        raise HTTPException(
            status_code=404,
            detail="This endpoint is only usable if there is exactly one user in the database",
        )

    await cruds_groups.create_membership(
        db=db,
        membership=schemas_core.CoreMembership(
            user_id=users[0].id, group_id=GroupType.admin
        ),
    )


@router.post(
    "/users/recover",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def recover_user(
    # We use embed for email parameter: https://fastapi.tiangolo.com/tutorial/body-multiple-params/#embed-a-single-body-parameter
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Allow an user to start a password reset process.

    If the provided **email** correspond to an existing account, a password reset token will be send.
    Using this token, the password can be changed with `/users/reset-password` endpoint
    """

    db_user = await cruds_users.get_user_by_email(db=db, email=email)
    if db_user is not None:
        # The user exist, we can send a password reset invitation
        reset_token = security.generate_token()

        recover_request = models_core.CoreUserRecoverRequest(
            email=email,
            user_id=db_user.id,
            reset_token=reset_token,
            created_on=datetime.now(),
            expire_on=datetime.now()
            + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS),
        )

        await cruds_users.create_user_recover_request(
            db=db, recover_request=recover_request
        )

        if settings.SMTP_ACTIVE:
            send_email(
                recipient=db_user.email,
                subject="MyECL - reset your password",
                content=f"You can reset your password with the token {reset_token}",
                settings=settings,
            )
        print(reset_token)

    return standard_responses.Result()


@router.post(
    "/users/reset-password",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def reset_password(
    reset_password_request: schemas_core.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset the user password, using a **reset_token** provided by `/users/recover` endpoint.
    """
    recover_request = await cruds_users.get_recover_request_by_reset_token(
        db=db, reset_token=reset_password_request.reset_token
    )
    if recover_request is None:
        raise HTTPException(status_code=404, detail="Invalid reset token")

    # We need to make sure the unconfirmed user is still valid
    if recover_request.expire_on < datetime.now():
        raise HTTPException(status_code=400, detail="Expired reset token")

    new_password_hash = security.get_password_hash(reset_password_request.new_password)
    await cruds_users.update_user_password_by_id(
        db=db, user_id=recover_request.user_id, new_password_hash=new_password_hash
    )

    # As the user has reset its password, all other recovery request can be deleted from the table
    await cruds_users.delete_recover_request_by_email(
        db=db, email=recover_request.email
    )

    return standard_responses.Result()


@router.post(
    "/users/change-password",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def change_password(
    change_password_request: schemas_core.ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Change a user password.

    This endpoint will check the **old_password**, see also `/users/reset-password` endpoint if the user forgot its password.
    """

    user = await security.authenticate_user(
        db=db,
        email=change_password_request.email,
        password=change_password_request.old_password,
    )
    if user is None:
        raise HTTPException(status_code=403, detail="The old password is invalid")

    new_password_hash = security.get_password_hash(change_password_request.new_password)
    await cruds_users.update_user_password_by_id(
        db=db,
        user_id=user.id,
        new_password_hash=new_password_hash,
    )

    return standard_responses.Result()


# We put the following endpoints at the end of the file to prevent them
# from interacting with the previous endpoints
# Ex: /users/activate is interpreted as a user whose id is "activate"


@router.get(
    "/users/{user_id}",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def read_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return `CoreUserSimple` representation of user with id `user_id`

    **The user must be authenticated to use this endpoint**
    """

    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# TODO: readd this after making sure all information about the user has been deleted
# @router.delete(
#    "/users/{user_id}",
#    status_code=204,
#    tags=[Tags.users],
# )
# async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin))):
#    """Delete user from database by id"""
#    # TODO: WARNING - deleting an user without removing its relations ship in other tables will have unexpected consequences
#
#    await cruds_users.delete_user(db=db, user_id=user_id)


@router.patch(
    "/users/me",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def update_current_user(
    user_update: schemas_core.CoreUserUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update the current user, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value

    **The user must be authenticated to use this endpoint**
    """

    await cruds_users.update_user(db=db, user_id=user.id, user_update=user_update)

    return user


@router.patch(
    "/users/{user_id}",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def update_user(
    user_id: str,
    user_update: schemas_core.CoreUserUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Update an user, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value

    **This endpoint is only usable by administrators**
    """
    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await cruds_users.update_user(db=db, user_id=user_id, user_update=user_update)

    return db_user


@router.post(
    "/users/me/profile-picture",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_current_user_profile_picture(
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
):
    """
    Upload a profile picture for the current user.

    **The user must be authenticated to use this endpoint**
    """

    if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400, detail="Invalid file format, supported jpeg, png and webp"
        )

    # We need to go to the end of the file to be able to get the size of the file
    image.file.seek(0, os.SEEK_END)
    # Use file.tell() to retrieve the cursor's current position
    file_size = image.file.tell()  # Bytes
    print(file_size)
    if file_size > 1024 * 1024 * 4:  # 4 MB
        raise HTTPException(
            status_code=413,
            detail="File size is too big. Limit is 4 MB",
        )
    # We go back to the beginning of the file to save it on the disk
    await image.seek(0)

    try:
        with open(f"data/profile-pictures/{user.id}.png", "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    except Exception as error:
        hyperion_error_logger.error(
            f"Create_current_user_profile_picture: could not save profile picture: {error} ({request_id})"
        )
        raise HTTPException(status_code=422, detail="Could not save profile picture")

    return standard_responses.Result(success=True)


@router.get(
    "/users/{user_id}/profile-picture/",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_user_profile_picture(
    user_id: str,
    # TODO: we may want to remove this user requirement to be able to display images easily in html code
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get the profile picture of an user.

    **The user must be authenticated to use this endpoint**
    """

    if not exists(f"data/profile-pictures/{user_id}.png"):
        return FileResponse("assets/images/default_profile_picture.png")

    return FileResponse(f"data/profile-pictures/{user_id}.png")

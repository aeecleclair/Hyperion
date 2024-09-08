import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import aiofiles
import calypsso
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core, security, standard_responses
from app.core.config import Settings
from app.core.groups import cruds_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    is_user,
    is_user_a_member_of,
    is_user_an_ecl_member,
)
from app.types.content_type import ContentType
from app.types.exceptions import UserWithEmailAlreadyExistError
from app.utils.mail.mailworker import send_email
from app.utils.tools import (
    create_and_send_email_migration,
    get_file_from_data,
    save_file_as_data,
    sort_user,
)

router = APIRouter(tags=["Users"])

hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")

templates = Jinja2Templates(directory="assets/templates")


@router.get(
    "/users/",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
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
    "/users/count",
    response_model=int,
    status_code=200,
)
async def count_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all users from database as a list of `CoreUserSimple`

    **This endpoint is only usable by administrators**
    """

    count = await cruds_users.count_users(db)
    return count


@router.get(
    "/users/search",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
)
async def search_users(
    query: str,
    includedGroups: list[str] = Query(default=[]),
    excludedGroups: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Search for a user using Jaro_Winkler distance algorithm. The

    `query` will be compared against users name, firstname and nickname

    **The user must be authenticated to use this endpoint**
    """

    users = await cruds_users.get_users(
        db,
        included_groups=includedGroups,
        excluded_groups=excludedGroups,
    )

    return sort_user(query, users)


@router.get(
    "/users/me",
    response_model=schemas_core.CoreUser,
    status_code=200,
)
async def read_current_user(
    user: models_core.CoreUser = Depends(is_user),
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
)
async def create_user_by_user(
    user_create: schemas_core.CoreUserCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Start the user account creation process. The user will be sent an email with a link to activate his account.
    > The received token needs to be sent to the `/users/activate` endpoint to activate the account.

    If the **password** is not provided, it will be required during the activation process. Don't submit a password if you are creating an account for someone else.

    When creating **student** or **staff** account a valid ECL email is required.
    Only admin users can create other **account types**, contact ÉCLAIR for more information.
    """
    # By default we mark the user as external
    # but if it has an ECL email address, we will mark it as member
    external = True
    # Check the account type

    # For staff and student
    # ^[\w\-.]*@((etu(-enise)?|enise)\.)?ec-lyon\.fr$
    # For staff
    # ^[\w\-.]*@(enise\.)?ec-lyon\.fr$
    # For student
    # ^[\w\-.]*@etu(-enise)?\.ec-lyon\.fr$

    # For former students
    # ^[\w\-.]*@centraliens-lyon\.net$

    # All accepted emails
    # ^[\w\-.]*@(((etu(-enise)?|enise)\.)?ec-lyon\.fr|centraliens-lyon\.net)$

    if re.match(r"^[\w\-.]*@(enise\.)?ec-lyon\.fr$", user_create.email):
        # Its a staff email address
        account_type = AccountType.staff
        external = False
    elif re.match(
        r"^[\w\-.]*@etu(-enise)?\.ec-lyon\.fr$",
        user_create.email,
    ):
        # Its a student email address
        account_type = AccountType.student
        external = False
    elif re.match(
        r"^[\w\-.]*@centraliens-lyon\.net$",
        user_create.email,
    ):
        # Its a former student email address
        account_type = AccountType.formerstudent
        external = False
    elif user_create.accept_external:
        account_type = AccountType.external
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid ECL email address.",
        )

    if not user_create.accept_external:
        if external:
            raise HTTPException(
                status_code=400,
                detail="The user could not be marked as external. Try to add accept_external=True in the request or use an internal email address.",
            )

    # Make sure a confirmed account does not already exist
    db_user = await cruds_users.get_user_by_email(db=db, email=user_create.email)
    if db_user is not None:
        hyperion_security_logger.warning(
            f"Create_user: an user with email {user_create.email} already exists ({request_id})",
        )
        # We will send to the email a message explaining they already have an account and can reset their password if they want.
        if settings.SMTP_ACTIVE:
            account_exists_content = templates.get_template(
                "account_exists_mail.html",
            ).render()
            background_tasks.add_task(
                send_email,
                recipient=user_create.email,
                subject="MyECL - your account already exists",
                content=account_exists_content,
                settings=settings,
            )

        # Fail silently: the user should not be informed that a user with the email address already exist.
        return standard_responses.Result(success=True)

    # There might be an unconfirmed user in the database but its not an issue. We will generate a second activation token.

    await create_user(
        email=user_create.email,
        account_type=account_type,
        background_tasks=background_tasks,
        db=db,
        settings=settings,
        request_id=request_id,
        external=external,
    )

    return standard_responses.Result(success=True)


@router.post(
    "/users/batch-creation",
    response_model=standard_responses.BatchResult,
    status_code=201,
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
                account_type=user_create.account_type,
                background_tasks=background_tasks,
                db=db,
                settings=settings,
                request_id=request_id,
                external=user_create.external,
            )
        except Exception as error:
            failed[user_create.email] = str(error)

    return standard_responses.BatchResult(failed=failed)


async def create_user(
    email: str,
    account_type: AccountType,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    settings: Settings,
    request_id: str,
    external: bool,
) -> None:
    """
    User creation process. This function is used by both `/users/create` and `/users/admin/create` endpoints
    """
    # Warning: the validation token (and thus user_unconfirmed object) should **never** be returned in the request

    # If an account already exist, we can not create a new one
    db_user = await cruds_users.get_user_by_email(db=db, email=email)
    if db_user is not None:
        raise UserWithEmailAlreadyExistError(email)
    # There might be an unconfirmed user in the database but its not an issue. We will generate a second activation token.

    activation_token = security.generate_token(nbytes=16)

    # Add the unconfirmed user to the unconfirmed_user table

    user_unconfirmed = models_core.CoreUserUnconfirmed(
        id=str(uuid.uuid4()),
        email=email,
        account_type=account_type,
        activation_token=activation_token,
        created_on=datetime.now(UTC),
        expire_on=datetime.now(UTC)
        + timedelta(hours=settings.USER_ACTIVATION_TOKEN_EXPIRE_HOURS),
        external=external,
    )

    await cruds_users.create_unconfirmed_user(user_unconfirmed=user_unconfirmed, db=db)

    # After adding the unconfirmed user to the database, we got an activation token that need to be send by email,
    # in order to make sure the email address is valid

    calypsso_activate_url = settings.CLIENT_URL + calypsso.get_activate_relative_url(
        activation_token=activation_token,
        external=external,
    )

    if settings.SMTP_ACTIVE:
        activation_content = templates.get_template("activation_mail.html").render(
            {"calypsso_activate_url": calypsso_activate_url},
        )
        background_tasks.add_task(
            send_email,
            recipient=email,
            subject="MyECL - confirm your email",
            content=activation_content,
            settings=settings,
        )
        hyperion_security_logger.info(
            f"Create_user: Creating an unconfirmed account for {email} ({request_id})",
        )
    else:
        hyperion_security_logger.info(
            f"Create_user: Creating an unconfirmed account for {email}: {calypsso_activate_url} ({request_id})",
        )


@router.post(
    "/users/activate",
    response_model=standard_responses.Result,
    status_code=201,
)
async def activate_user(
    user: schemas_core.CoreUserActivateRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """
    Activate the previously created account.

    **token**: the activation token sent by email to the user

    **password**: user password, required if it was not provided previously
    """
    # We need to find the corresponding user_unconfirmed
    unconfirmed_user = await cruds_users.get_unconfirmed_user_by_activation_token(
        db=db,
        activation_token=user.activation_token,
    )
    if unconfirmed_user is None:
        raise HTTPException(status_code=404, detail="Invalid activation token")

    # We need to make sure the unconfirmed user is still valid
    if unconfirmed_user.expire_on < datetime.now(UTC):
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

    # A password should have been provided
    password_hash = security.get_password_hash(user.password)

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
        created_on=datetime.now(UTC),
        external=unconfirmed_user.external,
    )
    # We add the new user to the database
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
        db=db,
        email=unconfirmed_user.email,
    )

    hyperion_security_logger.info(
        f"Activate_user: Activated user {confirmed_user.id} (email: {confirmed_user.email}) ({request_id})",
    )

    return standard_responses.Result()


@router.post(
    "/users/make-admin",
    response_model=standard_responses.Result,
    status_code=200,
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
            status_code=403,
            detail="This endpoint is only usable if there is exactly one user in the database",
        )

    try:
        await cruds_groups.create_membership(
            db=db,
            membership=models_core.CoreMembership(
                user_id=users[0].id,
                group_id=GroupType.admin,
            ),
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return standard_responses.Result()


@router.post(
    "/users/recover",
    response_model=standard_responses.Result,
    status_code=201,
)
async def recover_user(
    # We use embed for email parameter: https://fastapi.tiangolo.com/tutorial/body-multiple-params/#embed-a-single-body-parameter
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Allow a user to start a password reset process.

    If the provided **email** corresponds to an existing account, a password reset token will be sent.
    Using this token, the password can be changed with `/users/reset-password` endpoint
    """

    db_user = await cruds_users.get_user_by_email(db=db, email=email)
    if db_user is None:
        if settings.SMTP_ACTIVE:
            calypsso_register_url = (
                settings.CLIENT_URL
                + calypsso.get_register_relative_url(
                    external=True,
                )
            )

            reset_content = templates.get_template(
                "reset_mail_does_not_exist.html",
            ).render(
                {
                    "calypsso_register_url": calypsso_register_url,
                },
            )
            send_email(
                recipient=email,
                subject="MyECL - reset your password",
                content=reset_content,
                settings=settings,
            )
        else:
            hyperion_security_logger.info(
                f"Reset password failed for {email}, user does not exist",
            )

    else:
        # The user exists, we can send a password reset invitation
        reset_token = security.generate_token()

        recover_request = models_core.CoreUserRecoverRequest(
            email=email,
            user_id=db_user.id,
            reset_token=reset_token,
            created_on=datetime.now(UTC),
            expire_on=datetime.now(UTC)
            + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS),
        )

        await cruds_users.create_user_recover_request(
            db=db,
            recover_request=recover_request,
        )

        calypsso_reset_url = (
            settings.CLIENT_URL
            + calypsso.get_reset_password_relative_url(reset_token=reset_token)
        )

        if settings.SMTP_ACTIVE:
            reset_content = templates.get_template("reset_mail.html").render(
                {
                    "calypsso_reset_url": calypsso_reset_url,
                },
            )
            send_email(
                recipient=db_user.email,
                subject="MyECL - reset your password",
                content=reset_content,
                settings=settings,
            )
        else:
            hyperion_security_logger.info(
                f"Reset password for {email}: {calypsso_reset_url}",
            )

    return standard_responses.Result()


@router.post(
    "/users/reset-password",
    response_model=standard_responses.Result,
    status_code=201,
)
async def reset_password(
    reset_password_request: schemas_core.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset the user password, using a **reset_token** provided by `/users/recover` endpoint.
    """
    recover_request = await cruds_users.get_recover_request_by_reset_token(
        db=db,
        reset_token=reset_password_request.reset_token,
    )
    if recover_request is None:
        raise HTTPException(status_code=404, detail="Invalid reset token")

    # We need to make sure the unconfirmed user is still valid
    if recover_request.expire_on < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Expired reset token")

    new_password_hash = security.get_password_hash(reset_password_request.new_password)
    await cruds_users.update_user_password_by_id(
        db=db,
        user_id=recover_request.user_id,
        new_password_hash=new_password_hash,
    )

    # As the user has reset its password, all other recovery requests can be deleted from the table
    await cruds_users.delete_recover_request_by_email(
        db=db,
        email=recover_request.email,
    )

    return standard_responses.Result()


@router.post(
    "/users/migrate-mail",
    status_code=204,
)
async def migrate_mail(
    mail_migration: schemas_core.MailMigrationRequest,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    settings: Settings = Depends(get_settings),
):
    """
    Due to a change in the email format, all student users need to migrate their email address.
    This endpoint will send a confirmation code to the user's new email address. He will need to use this code to confirm the change with `/users/confirm-mail-migration` endpoint.
    """

    if not re.match(
        r"^[\w\-.]*@((ecl\d{2})|(alternance\d{4})|(master)|(auditeur))\.ec-lyon\.fr$",
        user.email,
    ):
        raise HTTPException(
            status_code=400,
            detail="Only student users with an old email address can migrate their email address",
        )

    if not re.match(r"^[\w\-.]*@etu(-enise)?\.ec-lyon\.fr$", mail_migration.new_email):
        raise HTTPException(
            status_code=400,
            detail="The new email address must match the new ECL format for student users",
        )

    existing_user = await cruds_users.get_user_by_email(
        db=db,
        email=mail_migration.new_email,
    )
    if existing_user is not None:
        hyperion_security_logger.info(
            f"Email migration: There is already an account with the email {mail_migration.new_email}",
        )
        if settings.SMTP_ACTIVE:
            migration_content = templates.get_template(
                "migration_mail_already_used.html",
            ).render({})
            send_email(
                recipient=mail_migration.new_email,
                subject="MyECL - Confirm your new email adresse",
                content=migration_content,
                settings=settings,
            )
        return

    await create_and_send_email_migration(
        user_id=user.id,
        new_email=mail_migration.new_email,
        old_email=user.email,
        db=db,
        settings=settings,
        make_user_external=user.external,
    )


@router.get(
    "/users/migrate-mail-confirm",
    status_code=200,
)
async def migrate_mail_confirm(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Due to a change in the email format, all student users need to migrate their email address.
    This endpoint will updates the user new email address.
    """

    migration_object = await cruds_users.get_email_migration_code_by_token(
        confirmation_token=token,
        db=db,
    )

    if migration_object is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid confirmation token for this user",
        )

    existing_user = await cruds_users.get_user_by_email(
        db=db,
        email=migration_object.new_email,
    )
    if existing_user is not None:
        hyperion_security_logger.info(
            f"Email migration: There is already an account with the email {migration_object.new_email}",
        )
        raise HTTPException(
            status_code=400,
            detail=f"There is already an account with the email {migration_object.new_email}",
        )

    try:
        await cruds_users.update_user_email_by_id(
            db=db,
            user_id=migration_object.user_id,
            new_email=migration_object.new_email,
            make_user_external=migration_object.make_user_external,
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))

    await cruds_users.delete_email_migration_code_by_token(
        confirmation_token=token,
        db=db,
    )

    async with aiofiles.open(
        "data/core/mail-migration-archives.txt",
        mode="a",
    ) as file:
        await file.write(
            f"{migration_object.user_id},{migration_object.old_email},{migration_object.new_email}\n",
        )

    return "The email address has been successfully updated"


@router.post(
    "/users/change-password",
    response_model=standard_responses.Result,
    status_code=201,
)
async def change_password(
    change_password_request: schemas_core.ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Change a user password.

    This endpoint will check the **old_password**, see also the `/users/reset-password` endpoint if the user forgot their password.
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
## )
# async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin))):
#    """Delete user from database by id"""
#    # TODO: WARNING - deleting an user without removing its relations ship in other tables will have unexpected consequences
#
#    await cruds_users.delete_user(db=db, user_id=user_id)


@router.post(
    "/users/me/ask-deletion",
    status_code=204,
)
async def delete_user(
    user: models_core.CoreUser = Depends(is_user),
):
    """
    This endpoint will ask administrators to process to the user deletion.
    This manual verification is needed to prevent data from being deleting for other users
    """
    hyperion_security_logger.info(
        f"User {user.email} - {user.id} has requested to delete their account.",
    )


@router.patch(
    "/users/me",
    status_code=204,
)
async def update_current_user(
    user_update: schemas_core.CoreUserUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Update the current user, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value

    **The user must be authenticated to use this endpoint**
    """

    await cruds_users.update_user(db=db, user_id=user.id, user_update=user_update)


@router.post(
    "/users/merge",
    status_code=204,
)
async def merge_users(
    user_fusion: schemas_core.CoreUserFusionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Fusion two users into one. The first user will be deleted and its data will be transferred to the second user.
    """
    hyperion_security_logger.info(
        f"User {user.email} - {user.id} has requested to merge {user_fusion.user_deleted_email} into {user_fusion.user_kept_email}",
    )
    user_kept = await cruds_users.get_user_by_email(
        db=db,
        email=user_fusion.user_kept_email,
    )
    if user_kept is None:
        raise HTTPException(status_code=404, detail="User kept not found")

    user_deleted = await cruds_users.get_user_by_email(
        db=db,
        email=user_fusion.user_deleted_email,
    )
    if user_deleted is None:
        raise HTTPException(status_code=404, detail="User deleted not found")

    await cruds_users.fusion_users(
        db=db,
        user_kept_id=user_kept.id,
        user_deleted_id=user_deleted.id,
    )
    background_tasks.add_task(
        send_email,
        recipient=[user_kept.email, user_deleted.email],
        subject="MyECL - Fusion de compte",
        content=f"Le compte {user_deleted.email} a été fusionné avec le compte {user_kept.email}. Tout le contenu du compte {user_deleted.email} a été transféré sur le compte {user_kept.email}.\nMerci de vous connecter avec le compte {user_kept.email} pour accéder à vos données.",
        settings=settings,
    )
    hyperion_security_logger.info(
        f"User {user_kept.email} - {user_kept.id} has been merged with {user_deleted.email} - {user_deleted.id}",
    )


@router.patch(
    "/users/{user_id}",
    status_code=204,
)
async def update_user(
    user_id: str,
    user_update: schemas_core.CoreUserUpdateAdmin,
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


@router.post(
    "/users/me/profile-picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_current_user_profile_picture(
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user),
    request_id: str = Depends(get_request_id),
):
    """
    Upload a profile picture for the current user.

    **The user must be authenticated to use this endpoint**
    """

    await save_file_as_data(
        upload_file=image,
        directory="profile-pictures",
        filename=str(user.id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)


@router.get(
    "/users/me/profile-picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_own_profile_picture(
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get the profile picture of the authenticated user.
    """

    return get_file_from_data(
        directory="profile-pictures",
        filename=str(user.id),
        default_asset="assets/images/default_profile_picture.png",
    )


@router.get(
    "/users/{user_id}/profile-picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_user_profile_picture(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the profile picture of an user.

    Unauthenticated users can use this endpoint (needed for some OIDC services)
    """

    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return get_file_from_data(
        directory="profile-pictures",
        filename=str(user_id),
        default_asset="assets/images/default_profile_picture.png",
    )

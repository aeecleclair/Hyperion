import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.cruds import cruds_users
from app.dependencies import get_db
from app.schemas import schemas_core
from app.utils.mail.mailworker import send_email
from app.utils.types import standard_responses
from app.utils.types.account_type import AccountType
from app.utils.types.tags import Tags
from app.core import security

router = APIRouter()


@router.get(
    "/users/",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
    tags=[Tags.users],
)
async def get_users(db: AsyncSession = Depends(get_db)):
    """Return all users from database as a list of CoreUserSimple"""

    users = await cruds_users.get_users(db)
    return users


@router.get(
    "/users/{user_id}",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Return user with id from database as a dictionary"""

    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete(
    "/users/{user_id}",
    status_code=204,
    tags=[Tags.users],
)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Delete user from database by id"""

    await cruds_users.delete_user(db=db, user_id=user_id)


@router.post(
    "/users/create",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users, "User creation"],
)
async def create_user(
    user_create: schemas_core.CoreUserCreateRequest, db: AsyncSession = Depends(get_db)
):
    """
    Start the user account creation process. The user will be sent an email with a link to activate his account.
    > The received token needs to be send to `/users/activate` endpoint to activate the account.

    If the **password** is not provided, it will be required during the activation process. Don't submit a password if you are creating an account for someone else.

    When creating **student** or **personnel** account a valid ECL email is required.
    Only admin users can create other **account types**, contact ÉCLAIR for more informations.
    """
    # Check the account type
    if (
        user_create.account_type == AccountType.eleve
        or user_create.account_type == AccountType.personnel
    ):
        # Students and personnels account should only be created with valid ECL address.
        # We compare to ".ec-lyon.fr" with a first dot to prevent someone from using a false domain (ex: pirate@other-ec-lyon.fr)
        if not user_create.email[-11:] == ".ec-lyon.fr":
            raise HTTPException(status_code=400, detail="Invalid ECL email address")
    else:
        # TODO: check if the user is admin
        raise HTTPException(
            status_code=403, detail=f"Unauthorized create a {user_create.type} account"
        )

    # Make sure a confirmed account does not already exist
    db_user = await cruds_users.get_user_by_email(db=db, email=user_create.email)
    if db_user is not None:
        # Fail silently
        raise HTTPException(status_code=422, detail="User already exist")

    password_hash = security.get_password_hash(user_create.password)
    activation_token = security.generate_token()

    # Add the unconfirmed user to the unconfirmed_user table
    try:
        user_unconfirmed = schemas_core.CoreUserUnconfirmedInDB(
            id=str(uuid.uuid4()),  # Use UUID later
            email=user_create.email,
            password_hash=password_hash,
            activation_token=activation_token,
            created_on=datetime.datetime.now(),
            expire_on=datetime.datetime.now()
            + datetime.timedelta(hours=settings.USER_ACTIVATION_TOKEN_EXPIRES_HOURS),
            account_type=user_create.account_type,
        )

        await cruds_users.create_unconfirmed_user(
            user_unconfirmed=user_unconfirmed, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    else:
        # After adding the unconfirmed user to the database, we got an activation token that need to be send by email,
        # in order to make sure the email address is valid

        # TODO
        # Send email in an other thread
        # Catch errors
        if settings.SMTP_ACTIVE:
            send_email(
                recipient=user_create.email,
                subject="MyECL - confirm your email",
                content=f"Please confirm your MyECL account with the token {activation_token}",
            )
        print(activation_token)

        # Warning: the validation token (and thus user_unconfirmed object) should **never** be returned by the request
        return standard_responses.Result(success=True)


@router.post(
    "/users/activate",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users, "User creation"],
)
async def activate_user(
    user: schemas_core.CoreUserActivateRequest, db: AsyncSession = Depends(get_db)
):
    """
    Activate the previously created account.
    **token**: the activation token send by email to the user
    **password**: user password, required if it was not provided previously
    """
    # We need to find the corresponding user_unconfirmed
    unconfirmed_user = await cruds_users.get_unconfirmed_user_by_activation_token(
        activation_token=user.activation_token, db=db
    )
    if unconfirmed_user is None:
        raise HTTPException(status_code=422, detail="Invalid activation token")

    # We need to make sure the unconfirmed user is still valid
    if unconfirmed_user.expire_on < datetime.datetime.now():
        raise HTTPException(status_code=422, detail="Expired activation token")

    # We need to make sure the password was provided at least once during the account creation process
    if unconfirmed_user.password_hash is None and user.password is None:
        raise HTTPException(status_code=422, detail="A password was never provided")

    # If a password was provided in this request, we will use this one as it is more recent
    if user.password is not None:
        password_hash = security.get_password_hash(user.password)
    else:
        password_hash = unconfirmed_user.password_hash

    print(unconfirmed_user.account_type)

    confirmed_user = schemas_core.CoreUserInDB(
        **user.dict(),
        email=unconfirmed_user.email,
        id=unconfirmed_user.id,
        password_hash=password_hash,
        created_on=datetime.datetime.now(),
    )
    # We add the new user to the database
    await cruds_users.create_user(db=db, user=confirmed_user)

    # We remove all unconfirmed users with the same email address
    await cruds_users.delete_unconfirmed_user_by_email(
        db=db, email=unconfirmed_user.email
    )

    return standard_responses.Result()


@router.post(
    "/users/recover",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users, "User creation"],
)
async def recover_user(email: str, db: AsyncSession = Depends(get_db)):
    """
    Allow an user to start a password reset process.

    If the provided **email** correspond to an existing account, a password reset token will be send.
    Using this token, the password can be changed with `/users/reset-password` endpoint

    """
    db_user = await cruds_users.get_user_by_email(db=db, email=email)
    if db_user is not None:
        # The user exist, we can send a password reset invitation
        reset_token = security.generate_token()

        recover_request = schemas_core.CoreUserRecoverRequest(
            email=email,
            user_id=db_user.id,
            reset_token=reset_token,
            created_on=datetime.datetime.now(),
            expire_on=datetime.datetime.now()
            + datetime.timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRES_HOURS),
        )

        cruds_users.create_user_recover_request(db=db, recover_user=recover_request)

        if settings.SMTP_ACTIVE:
            send_email(
                recipient=db_user.email,
                subject="MyECL - reset your password",
                content=f"You can reset your password with the token {reset_token}",
            )
        print(reset_token)

    return standard_responses.Result()


@router.post(
    "/users/reset-password",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users, "User creation"],
)
async def reset_password_user(
    reset_token: str, new_password: str, db: AsyncSession = Depends(get_db)
):
    """
    Reset the user password, using a **reset_token** provided by `/users/recover` endpoint.
    """
    recover_request = await cruds_users.get_recover_request_by_reset_token(
        reset_token == reset_token, db=db
    )
    if recover_request is None:
        raise HTTPException(status_code=422, detail="Invalid reset token")

    # We need to make sure the unconfirmed user is still valid
    if recover_request.expire_on < datetime.datetime.now():
        raise HTTPException(status_code=422, detail="Expired reset token")

    new_password_hash = get_password_hash(new_password)
    cruds_users.update_user_password_by_id(
        db=db, id=recover_request.user_id, new_password_hash=new_password_hash
    )

    # As the user has reset its password, all other recovery request can be deleted from the table
    cruds_users.delete_recover_request_by_email(db=db, email=recover_request.email)

    return standard_responses.Result()

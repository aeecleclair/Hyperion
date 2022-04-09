import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash
from app.dependencies import get_db
from app.cruds import cruds_users
from app.dependencies import get_db
from app.schemas import schemas_core
from app.utils.types.tags import Tags
from app.utils.types.account_type import AccountType
from app.utils.types import standard_responses
from app.utils.mail.mailworker import send_email_background, send_email_async
from starlette.responses import JSONResponse


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


"""
@router.post(
    "/users/",
    response_model=schemas_core.CoreUserSimple,
    status_code=201,
    tags=[Tags.users],
)
async def create_user(
    user: schemas_core.CoreUserCreate, db: AsyncSession = Depends(get_db)
):
    \"""Create a new user in database and return it as a CoreUserSimple\"""
    try:
        return await cruds_users.create_user(user=user, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
"""


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
    user: schemas_core.CoreUserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Start the user account creation process. The user will be sent an email with a link to activate his account.
    The received token need to be send to `/users/activate` endpoint to activate the account.
    """
    # Check the account type
    if (
        user.account_type == AccountType.eleve
        or user.account_type == AccountType.personnel
    ):
        # Students and personnels account should only be created with valid ECL address.
        # We compare to ".ec-lyon.fr" with a first dot to prevent someone from using a false domain (ex: pirate@other-ec-lyon.fr)
        if not user.email[-11:] == ".ec-lyon.fr":
            raise HTTPException(status_code=400, detail="Invalid ECL email address")
    else:
        # TODO: check if the user is admin
        raise HTTPException(
            status_code=403, detail=f"Unauthorized create a {user.type} account"
        )

    # Make sure a confirmed account does not already exist
    db_user = await cruds_users.get_user_by_email(db=db, email=user.email)
    if db_user is not None:
        raise HTTPException(status_code=422, detail="User already exist")

    # Add the unconfirmed user to the unconfirmed_user table
    try:
        user_unconfirmed = await cruds_users.create_unconfirmed_user(user=user, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    else:
        # After adding the unconfirmed user to the database, we got an activation token that need to be send by email,
        # in order to make sure the email address is valid

        # send_email(to=user_unconfirmed.email)  # TODO: catch errors
        await send_email_async(
            "Vérifier votre email",
            user_unconfirmed.email,
            {
                "title": "MyECL",
                "name": str(user_unconfirmed.first_name) + str(user_unconfirmed.name),
            },
        )
        print(user_unconfirmed.activation_token)

        # Warning: the validation token (and thus user_unconfirmed object) should **never** be returned by the request
        return standard_responses.Result(success=True)

        # Make sure the token is only used once
        # Make sur we can not create a token for an unexisting account


@router.post(
    "/users/activate",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users, "User creation"],
)
async def activate_user(
    user: schemas_core.CoreUserActivate, db: AsyncSession = Depends(get_db)
):
    # We need to find the corresponding user_unconfirmed
    unconfirmed_user = await cruds_users.get_unconfirmed_user_by_activation_token(
        activation_token=user.activation_token, db=db
    )
    print(unconfirmed_user)
    if unconfirmed_user is None:
        raise HTTPException(status_code=422, detail="Invalid user or activation token")

    print("Time", unconfirmed_user.expire_on)
    print(datetime.datetime.now())

    # We need to make sure the unconfirmed user is still valid
    if unconfirmed_user.expire_on < datetime.datetime.now():
        raise HTTPException(status_code=422, detail="Expired activation token")

    # We need to make sure the password was provided at least once during the account creation process
    if unconfirmed_user.password_hash is None and user.password is None:
        raise HTTPException(status_code=422, detail="A password was never provided")

    # If a password was provided in this request, we will use this one as it is more recent
    if user.password is not None:
        password_hash = get_password_hash(user.password)
    else:
        password_hash = unconfirmed_user.password_hash

    print(unconfirmed_user.account_type)

    confirmed_user = schemas_core.CoreUserInDB(
        name=user.name,
        firstname=user.firstname,
        nickname=user.nickname,
        email=unconfirmed_user.email,
        birthday=user.birthday,
        phone=user.phone,
        promo=user.promo,
        floor=user.floor,
        id=unconfirmed_user.id,
        password_hash=password_hash,
        account_type=unconfirmed_user.account_type,
        created_on=datetime.datetime.now(),
    )
    # We add the new user to the database
    await cruds_users.create_user(db=db, user=confirmed_user)

    # We remove all unconfirmed users with the same email address
    await cruds_users.delete_unconfirmed_user_by_email(
        db=db, email=unconfirmed_user.email
    )

    return standard_responses.Result()


@router.get("/sendemail/asynchronous")
async def send_email_asynchronous():
    await send_email_async(
        "Verifier votre email",
        "victor.angot@gmail.com",
        {"title": "Hello World", "name": "John Doe"},
    )
    return JSONResponse(status_code=200, content={"message": "email has been sent"})


@router.get("/send-email/backgroundtasks")
def send_email_backgroundtasks(background_tasks: BackgroundTasks):
    """Send an email asynchronously using background tasks. Use this mail sender for notifications for instance"""
    send_email_background(
        background_tasks,
        "Hello World",
        "someemail@gmail.com",
        {"title": "Hello World", "name": "John Doe"},
    )
    return JSONResponse(status_code=200, content={"message": "email has been sent"})

from fastapi import APIRouter, Depends, status, HTTPException, Request, Body
from fastapi.responses import RedirectResponse
from app.core.security import create_access_token

from app.core.security import authenticate_user, create_access_token
from app.dependencies import get_db, get_settings
from app.schemas import schemas_core
from app.utils.types.tags import Tags
from app.core.security import generate_token
from fastapi.templating import Jinja2Templates
from app.cruds import cruds_auth
from app.models import models_core
from datetime import datetime, timedelta
from app.schemas import schemas_core

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.post(
    "/auth/token",
    response_model=schemas_core.AccessToken,
    status_code=200,
    tags=[Tags.auth],
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Ask for a JWT access token using oauth password flow.

    *username* and *password* must be provided

    Note: the request body needs to use **form-data** and not json.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # We put the user id in the subject field of the token.
    # The subject `sub` is a JWT registered claim name, see https://datatracker.ietf.org/doc/html/rfc7519#section-4.1
    access_token = create_access_token(
        data={"sub": user.id}, settings=Depends(get_settings)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Authorization Code Grant #

# Terminology:
# Authorization Code Grant: a type of oauth flow. Usefull for server served webapp or mobile app
# Client: the entity which want to get an authorization to some ressource from the ressource server owned by an user
# Ressource server: the entity that can serve ressources in exchange for a token, ex: a user profil. Here it's Hyperion
# Authorization server: the entity that is in charge of authorization. Using a oauth flow, it will give tokens.

# https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/
# https://www.oauth.com/oauth2-servers/server-side-apps/example-flow/


# http://127.0.0.1:8000/auth/authorize-page?response_type=code&client_id=1234&redirect_uri=h&scope=&state=
@router.get(
    "/auth/authorization-flow/authorize-page",
)
async def authorize_page(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    request: Request,
):
    """
    This endpoint is the one the user is redirected to when begining the authorization process.
    The page should allow the user to login and choose if he want to authorize the client

    The following query parameters are required for Oauth2 Authorization Code Grant flow.
    They need to be passed to the authorization endpoint `/auth/authorize`
    ```python
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    ```

    **This endpoint is an UI endpoint and is not part of the authorization exchanges**
    """
    return templates.TemplateResponse(
        "connexion.html",
        {
            "request": request,
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        },
    )


@router.get(
    "/auth/authorization-flow/authorize",
)
async def authorize(
    email: str,
    password: str,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Part 1 of the authorization code grant.

    Query parameters includes:

    * parameters for the client which want to get an authorization:
    ```python
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    ```

    * parameters that allows to authenticate the user and know which scopes it want to grant access to.
    ```python
    email: str,
    password: str,
    ```
    Note: we may want to require a JWT here, instead of email/password!
    Note: we should add a way to indicate which ressources the client should be granted access
    """

    # Request example from Nextcloud social login app
    # ?response_type=code&client_id=myeclnextcloud&redirect_uri=http://localhost:8009/apps/sociallogin/custom_oauth2/myecl&scope=&state=HA-HJIDEGL6MQTCW2B3Z8914OUN5X0SPVYR7KAF

    # We need to authenticate the user here:
    # TODO: we should not use the password like this
    user = await authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Oauth authorization code grant expect to return an authorization *code*
    if response_type != "code":
        raise HTTPException(status_code=422, detail="Invalid response_type")

    # We want to check `client_id`. Generally clients have to be registered in the authorization server
    # TODO

    # We generate a new authorization_code
    authorization_code = generate_token()
    expire_on = datetime.now() + timedelta(hours=1)

    # We save this authorization_code to the database
    # TODO: could we use a JWT?
    db_authorization_code = models_core.AuthorizationCode(
        code=authorization_code, expire_on=expire_on
    )
    await cruds_auth.create_authorization_token(
        db=db, db_authorization_code=db_authorization_code
    )

    # We need to redirect to the `redirect_uri` provided by the *client* providing the new authorization_code.
    # For security reason, we need to provide the same `state` that was send by the client in the first request
    url = (
        redirect_uri.replace("%3A", ":").replace("%2F", "/")
        + "?code="
        + authorization_code
        + "&state="
        + state
    )
    return RedirectResponse(url)


# TODO: NOT IMPLEMENTED!
@router.post("/auth/authorization-flow/token")
async def authorization_flow_token(
    # res: schemas_core.TokenReq,
    request: Request,
):  # productId: int = Body(...)):  # , request: Request):
    """
    Part 3 of the authorization code grant.
    The client ask to exchange its authorization code for an access token
    """
    # TODO: NOT IMPLEMENTED!

    # print(await request.json())
    # print(request)
    return {
        "access_token": "AYjcyMzY3ZDhiNmJkNTY",
        "refresh_token": "RjY2NjM5NzA2OWJjuE7c",
        "token_type": "Bearer",
        "expires": 3600,
    }


# TODO: NOT IMPLEMENTED!
@router.get(
    "/auth/profil",
)
async def profil(request: Request):
    # TODO: NOT IMPLEMENTED!

    # Fields are :
    # https://github.com/zorn-v/nextcloud-social-login/blob/e0e6deef8288daf04f557c0f124c63b6e975f0c0/lib/Provider/CustomOAuth2.php
    return {
        "identifier": "12345678910",
        "name": "Jhobahtes",
        "username": "Jhobahtes",
        "family_name": "Jhobahtes",
        "picture": "https://lh4.googleusercontent.com/-kw-iMgDj34/AAAAAAAAAAI/AAAAAAAAAAc/P1YY91tzesU/photo.jpg",
        "email": "Jhobahtes@myecl",
        "email_verified": True,
        "locale": "en",
        "hd": "okta.com",
    }

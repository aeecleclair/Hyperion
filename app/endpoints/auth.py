import base64
import hashlib
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Type

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_access_token_RS256,
    generate_token,
)
from app.cruds import cruds_auth
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    get_token_data,
    get_user_from_token_with_scopes,
)
from app.models import models_auth, models_core
from app.schemas import schemas_auth
from app.utils.auth.providers import BaseAuthClient
from app.utils.types.scopes_type import ScopeType
from app.utils.types.tags import Tags

router = APIRouter()

templates = Jinja2Templates(directory="templates")

logger = logging.getLogger("hyperion.auth")


# WARNING: if new flow are added, openid_config should be updated accordingly


# TODO: maybe remove
@router.post(
    "/auth/simple_token",
    response_model=schemas_auth.AccessToken,
    status_code=200,
    tags=[Tags.auth],
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Ask for a JWT acc   ess token using oauth password flow.

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
    data = schemas_auth.TokenData(sub=user.id, scopes=ScopeType.API)
    access_token = create_access_token(settings=settings, data=data)
    return {"access_token": access_token, "token_type": "bearer"}


# Authorization Code Grant #

# Terminology:
# Authorization Code Grant: a type of oauth flow. Usefull for server served webapp or mobile app
# Client: the entity which want to get an authorization to some ressource from the ressource server owned by an user
# Ressource server: the entity that can serve ressources in exchange for a token, ex: a user profil. Here it's Hyperion
# Authorization server: the entity that is in charge of authorization. Using a oauth flow, it will give tokens.

# https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/
# https://www.oauth.com/oauth2-servers/server-side-apps/example-flow/


# Authentication Request
# Common to OAuth 2.0 and OIDC


@router.get(
    "/auth/authorize",
    tags=[Tags.auth],
    response_class=HTMLResponse,
)
async def get_authorize_page(
    # request need to be passed to Jinja2 to generate the HTML page
    request: Request,
    authorizereq: schemas_auth.Authorize,
):
    """
    This endpoint is the one the user is redirected to when he begin the Oauth or Openid connect (*oidc*) *Authorization code* process.
    The page allows the user to login and may let the user choose what type of data he want to authorize the client for.

    This is the endpoint that should be set in the client OAuth or OIDC configuration page. It can be called by a GET or a POST request.

    See `/auth/authorization-flow/authorize-validation` endpoint for information about the parameters.

    **This endpoint is an UI endpoint which send and html page response. It will redirect to `/auth/authorization-flow/authorize-validation`**
    """

    return templates.TemplateResponse(
        "connexion.html",
        {
            "request": request,
            "response_type": authorizereq.response_type,
            "redirect_uri": authorizereq.redirect_uri,
            "client_id": authorizereq.client_id,
            "scope": authorizereq.scope,
            "state": authorizereq.state,
            "nonce": authorizereq.nonce,
            "code_challenge": authorizereq.code_challenge,
            "code_challenge_method": authorizereq.code_challenge_method,
        },
    )


@router.post(
    "/auth/authorize",
    tags=[Tags.auth],
    response_class=HTMLResponse,
)
async def post_authorize_page(
    # request need to be passed to Jinja2 to generate the HTML page
    request: Request,
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str | None = Form(None),
    state: str | None = Form(None),
    nonce: str | None = Form(None),
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form(None),
):
    """
    This endpoint is the one the user is redirected to when he begin the OAuth or Openid connect (*oidc*) *Authorization code* process with or without PKCE.
    The page allows the user to login and may let the user choose what type of data he want to authorize the client for.

    This is the endpoint that should be set in the client OAuth or OIDC configuration page. It can be called by a GET or a POST request.

    See `/auth/authorization-flow/authorize-validation` endpoint for information about the parameters.

    **This endpoint is an UI endpoint which send and html page response. It will redirect to `/auth/authorization-flow/authorize-validation`**
    """

    return templates.TemplateResponse(
        "connexion.html",
        {
            "request": request,
            "response_type": response_type,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "scope": scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        },
    )


@router.post(
    "/auth/authorization-flow/authorize-validation",
    tags=[Tags.auth],
    response_class=RedirectResponse,
)
async def authorize_validation(
    # User validation
    authorizereq: schemas_auth.AuthorizeValidation = Depends(
        schemas_auth.AuthorizeValidation.as_form
    ),
    # Database
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Part 1 of the authorization code grant.

    Parameters must be `application/x-www-form-urlencoded` and includes:

    * parameters for OAuth and Openid connect:
        * `response_type`: must be `code`
        * `client_id`: client identifier, needs to be registered in the server known_clients
        * `redirect_uri`: optional for OAuth (when registered in known_clients) but required for oidc. The url we need to redirect the user to after the authorization.
        * `scope`: optional for OAuth, must contain "openid" for oidc. List of scope the client want to get access to.
        * `state`: recommended. Opaque value used to maintain state between the request and the callback.

    * additional parameters for Openid connect:
        * `nonce`: oidc only. A string value used to associate a client session with an ID Token, and to mitigate replay attacks.

    * additional parameters for PKCE (see specs on https://datatracker.ietf.org/doc/html/rfc7636/):
        * `code_challenge`: PKCE only
        * `code_challenge_method`: PKCE only


    * parameters that allows to authenticate the user and know which scopes he grants access to.
        * `email`
        * `password`

    References:
     * https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2
     * https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
    """

    """
    If the request fails due to a missing, invalid, or mismatching
    redirection URI, or if the client identifier is missing or invalid,
    the authorization server SHOULD inform the resource owner of the
    error and MUST NOT automatically redirect the user-agent to the
    invalid redirection URI.
    """

    # Note: we may want to use a JWT here instead or email/password in order to be able to check if the user is already logged in.
    # Note: we may want add a windows to let the user which scopes he grants access to.

    logger.info(
        f"Authorize-validation: Starting for client {authorizereq.client_id} ({request_id})"
    )

    # Check if the client is registered in the server. auth_client will be None if the client_id is not known.
    auth_client: Type[BaseAuthClient] | None = settings.KNOWN_AUTH_CLIENTS.get(
        authorizereq.client_id
    )
    if auth_client is None:
        # The client does not exist
        logger.warning(
            f"Authorize-validation: Invalid client_id {authorizereq.client_id} ({request_id})"
        )
        raise HTTPException(
            status_code=422,
            detail="Invalid client_id",
        )

    # If a redirect_uri is hardcoded in the auth_client we will use this one. If one was provided in the request, we want to make sure they match.
    if auth_client.redirect_uri is not None:
        if authorizereq.redirect_uri is not None:
            if auth_client.redirect_uri != authorizereq.redirect_uri:
                logger.warning(
                    f"Authorize-validation: Mismatching redirect_uri, received {authorizereq.redirect_uri} but expected {auth_client.redirect_uri} ({request_id})"
                )
                raise HTTPException(
                    status_code=422,
                    detail="Mismatching redirect_uri",
                )
        redirect_uri = auth_client.redirect_uri
    else:
        # A redirect_uri must be provided in the request, as none are hardcoded in the auth_client
        if authorizereq.redirect_uri is None:
            logger.info(f"Authorize-validation: Unprovided redirect_uri ({request_id})")
            raise HTTPException(
                status_code=422,
                detail="Unprovided redirect_uri",
            )
        redirect_uri = authorizereq.redirect_uri

    # Special characters like `:` or `/` may be encoded as `%3A` and `%2F`, we need to decode them before returning the redirection object
    redirect_uri = urllib.parse.unquote(redirect_uri)

    # Currently, `code` is the only flow supported
    if authorizereq.response_type != "code":
        logger.warning(
            f"Authorize-validation: Unsupported response_type, received {authorizereq.response_type} ({request_id})"
        )
        url = redirect_uri + "?error=" + "unsupported_response_type"
        if authorizereq.state:
            url += "&state=" + authorizereq.state
        return RedirectResponse(url)

    # TODO: Currently if the user enter the wrong credentials in the form, he won't be redirected to the login page again but the OAuth process will fail.
    user = await authenticate_user(db, authorizereq.email, authorizereq.password)
    if not user:
        logger.warning(
            f"Authorize-validation: Invalide user email or password for email {authorizereq.email} ({request_id})"
        )
        url = redirect_uri + "?error=" + "unsupported_response_type"
        if authorizereq.state:
            url += "&state=" + authorizereq.state
        return RedirectResponse(url)

    # We generate a new authorization_code
    # The authorization code MUST expire
    # shortly after it is issued to mitigate the risk of leaks. A
    # maximum authorization code lifetime of 10 minutes is
    # RECOMMENDED. The client MUST NOT use the authorization code more than once.
    authorization_code = generate_token()
    expire_on = datetime.now() + timedelta(minutes=7)
    # We save this authorization_code to the database
    # We can not use a JWT for this as:
    # - we need to store data about the OAuth/oidc request
    # - we need to invalidate the token after its utilisation
    # TODO: we need to remove the token from the db after its expiration
    db_authorization_code = models_auth.AuthorizationCode(
        code=authorization_code,
        expire_on=expire_on,
        scope=authorizereq.scope,
        redirect_uri=redirect_uri,
        user_id=user.id,
        nonce=authorizereq.nonce,
        code_challenge=authorizereq.code_challenge,
        code_challenge_method=authorizereq.code_challenge_method,
    )
    await cruds_auth.create_authorization_token(
        db=db, db_authorization_code=db_authorization_code
    )

    # We need to redirect to the `redirect_uri` provided by the *client* providing the new authorization_code.
    # For security reason, we need to provide the same `state` and `nonce` if they were provided by the client in the first request
    url = redirect_uri + "?code=" + authorization_code
    if authorizereq.state:
        url += "&state=" + authorizereq.state
    # We need to redirect the user with as a GET request.
    # By default RedirectResponse send a 307 code, which prevent the user browser from changing the POST of this endpoint to a GET
    # We specifically return a 302 code to allow the user browser to change the POST of this endpoint to a GET
    # See https://stackoverflow.com/a/65512571
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/auth/token",
    tags=[Tags.auth],
    response_model=schemas_auth.TokenResponse,
    response_model_exclude_none=True,
)
async def token(
    response: Response,
    # OAuth and Openid connect parameters
    # The client id and secret must be passed either in the authorization header or with client_id and client_secret parameters
    tokenreq: schemas_auth.TokenReq = Depends(schemas_auth.TokenReq.as_form),
    authorization: str | None = Header(default=None),
    # Database
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Part 2 of the authorization code grant.
    The client exchange its authorization code for an access token. The endpoint support OAuth and Openid connect, with or without PKCE.

    Parameters must be `application/x-www-form-urlencoded` and includes:

    * parameters for OAuth and Openid connect:
        * `grant_type`: must be `authorization_code` or `refresh_token`
        * `code`: the authorization code received from the authorization endpoint
        * `redirect_uri`: optional for OAuth (when registered in known_clients) but required for oidc. The url we need to redirect the user to after the authorization. If provided, must be the same as previously registered in the `redirect_uri` field of the client.

    * Client credentials
        The client must send either:
            the client id and secret in the authorization header or with client_id and client_secret parameters

    * additional parameters for PKCE:
        * `code_verifier`: PKCE only, allows to verify the previous code_challenge

    https://datatracker.ietf.org/doc/html/rfc6749#section-4.1.3
    https://openid.net/specs/openid-connect-core-1_0.html#TokenRequestValidation
    """

    # We need to check client id and secret
    if authorization is not None:
        # client_id and client_secret are base64 encoded in the Basic authorization header
        tokenreq.client_id, tokenreq.client_secret = (
            base64.b64decode(authorization.replace("Basic ", ""))
            .decode("utf-8")
            .split(":")
        )

    logger.info(
        f"Token: Starting {tokenreq.grant_type} grant for client {tokenreq.client_id} ({request_id})"
    )

    if tokenreq.grant_type == "authorization_code":
        return await authorization_code_grant(
            db=db,
            settings=settings,
            tokenreq=tokenreq,
            response=response,
            request_id=request_id,
        )

    elif tokenreq.grant_type == "refresh_token":
        return await refresh_token_grant(
            db=db,
            settings=settings,
            tokenreq=tokenreq,
            response=response,
        )

    else:
        logger.warning(
            f"Token: Unsupported grant_type, received {tokenreq.grant_type} ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": f"{tokenreq.grant_type} is not supported",
            },
        )


async def authorization_code_grant(
    db: AsyncSession,
    settings: Settings,
    tokenreq: schemas_auth.TokenReq,
    response: Response,
    request_id: str,
):

    if tokenreq.code is None:
        logger.warning(
            f"Token authorization_code_grant: Unprovided authorization code ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "An authorization code should be provided",
            },
        )

    # We need to check the authorization code that was provided in the request is the one that was previously saved in the database
    db_authorization_code = await cruds_auth.get_authorization_token_by_token(
        db=db, code=tokenreq.code
    )
    if db_authorization_code is None:
        logger.warning(
            f"Token authorization_code_grant: Invalid authorization code ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "The provided authorization code is invalid",
            },
        )

    # The authorization code should only be usable once
    # We want to remove it from the database even if the request fail.
    # That's why we delete it at the beginning of this function
    await cruds_auth.delete_authorization_token_by_token(db=db, code=tokenreq.code)

    if tokenreq.client_id is None:
        logger.warning(
            f"Token authorization_code_grant: Unprovided client_id ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_client",
                "error_description": "Invalid client_id or secret",
            },
        )

    auth_client: Type[BaseAuthClient] | None = settings.KNOWN_AUTH_CLIENTS.get(
        tokenreq.client_id
    )

    if auth_client is None:
        logger.warning(
            f"Token authorization_code_grant: Invalid client_id {tokenreq.client_id} ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_client",
                "error_description": "Invalid client id or secret",
            },
        )

    # If the auth provider expect to use a client secret, we don't use PKCE
    elif auth_client.secret is not None:
        # As PKCE is not used, we need to make sure that PKCE related parameters were not used
        if (
            db_authorization_code.code_challenge is not None
            or tokenreq.code_verifier is not None
        ):
            logger.warning(
                f"Token authorization_code_grant: PKCE related parameters should not be used when using a client secret ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "PKCE related parameters should not be used",
                },
            )
        # We need to check the correct client_secret was provided
        if auth_client.secret != tokenreq.client_secret:
            logger.warning(
                f"Token authorization_code_grant: Invalid secret for client {tokenreq.client_id} ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_client",
                    "error_description": "Invalid client id or secret",
                },
            )

    # If there is no client secret, we use PKCE
    elif (
        db_authorization_code.code_challenge is not None
        and tokenreq.code_verifier is not None
    ):
        # As PKCE is used, we make sure a client secret was not provided
        if tokenreq.client_secret is not None:
            logger.warning(
                f"Token authorization_code_grant: A client secret should not be used when using PKCE ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "A client secret should not be used with PKCE",
                },
            )
        # We need to verify the hash correspond
        if (
            db_authorization_code.code_challenge
            != hashlib.sha256(tokenreq.code_verifier.encode()).hexdigest()
            # We need to pass the code_verifier as a b-string, we use `code_verifier.encode()` for that
            # TODO: Make sure that `.hexdigest()` is applied by the client to code_challenge
        ):
            logger.warning(
                f"Token authorization_code_grant: Invalid code_verifier ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "Invalid code_verifier",
                },
            )
    else:
        logger.warning(
            f"Token authorization_code_grant: Client must provide a client_secret or a code_verifier ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Client must provide a client_secret or a code_verifier",
            },
        )

    # We can check the authorization code
    if db_authorization_code.expire_on < datetime.now():
        logger.warning(
            f"Token authorization_code_grant: Expired authorization code ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Expired authorization code",
            },
        )

    # A redirect_uri may be hardcoded in the client
    if auth_client.redirect_uri is not None:
        if tokenreq.redirect_uri is None:
            # We use the hardcoded value
            tokenreq.redirect_uri = auth_client.redirect_uri
        # If a redirect_uri is provided, it should match the one in the auth client
        if tokenreq.redirect_uri != auth_client.redirect_uri:
            logger.warning(
                f"Token authorization_code_grant: redirect_uri {tokenreq.redirect_uri} do not match hardcoded redirect_uri ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "redirect_uri do not match",
                },
            )

    # If a redirect_uri was provided in the previous request, we need to check they match
    # > Ensure that the redirect_uri parameter value is identical to the redirect_uri parameter value that was included in the initial Authorization Request.
    # > If the redirect_uri parameter value is not present when there is only one registered redirect_uri value, the Authorization Server MAY return an error (since the Client should have included the parameter) or MAY proceed without an error (since OAuth 2.0 permits the parameter to be omitted in this case).
    if db_authorization_code.redirect_uri is not None:
        if tokenreq.redirect_uri is None:
            # We use the value provided previously
            tokenreq.redirect_uri = db_authorization_code.redirect_uri
        # If a redirect_uri is provided, it should match the one in the auth client
        if tokenreq.redirect_uri != db_authorization_code.redirect_uri:
            logger.warning(
                f"Token authorization_code_grant: redirect_uri {tokenreq.redirect_uri} do not match the redirect_uri provided previously {db_authorization_code.redirect_uri} ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "redirect_uri should remain identical",
                },
            )

    # If tokenreq.redirect_uri is still None, we should raise an error as we don't know which uri t use
    if tokenreq.redirect_uri is None:
        logger.warning(
            f"Token authorization_code_grant: redirect_uri was never provided ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "redirect_uri was never provided",
            },
        )

    refresh_token = generate_token()
    new_db_refresh_token = models_auth.RefreshToken(
        token=refresh_token,
        client_id=tokenreq.client_id,
        created_on=datetime.now(),
        user_id=db_authorization_code.user_id,
        expire_on=datetime.now()
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        scope=db_authorization_code.scope,
        nonce=db_authorization_code.nonce,
    )
    await cruds_auth.create_refresh_token(db=db, db_refresh_token=new_db_refresh_token)

    response_body = create_response_body(
        db_authorization_code, tokenreq.client_id, refresh_token, settings
    )

    # Required headers by Oauth and oidc
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response_body


async def refresh_token_grant(
    db: AsyncSession,
    settings: Settings,
    tokenreq: schemas_auth.TokenReq,
    response: Response,
    request_id: str,
):
    # Why doesn't this step use PKCE: https://security.stackexchange.com/questions/199000/oauth2-pkce-can-the-refresh-token-be-trusted
    # Answer in the link above: PKCE has been implemented because the authorization code could be intercepted, but since the refresh token is exchanged through a secure channel there is no issue here
    if tokenreq.refresh_token is None:
        logger.warning(
            f"Token refresh_token_grant: refresh_token was not provided ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "refresh_token is required",
            },
        )

    db_refresh_token = await cruds_auth.get_refresh_token_by_token(
        db=db, token=tokenreq.refresh_token
    )

    if db_refresh_token is None:
        logger.warning(
            f"Token refresh_token_grant: invalid refresh token ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Invalid refresh token",
            },
        )
    elif db_refresh_token.revoked_on is not None:
        # If the client try to use a revoked refresh_token, we want to revoke all other refresh tokens from this client
        # TODO: problematic loop
        await cruds_auth.revoke_refresh_token_by_client_id(
            db=db, client_id=db_refresh_token.client_id
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "The provided refresh token has been revoked",
            },
        )

    await cruds_auth.revoke_refresh_token_by_token(db=db, token=tokenreq.refresh_token)

    if db_refresh_token.expire_on < datetime.now():
        await cruds_auth.revoke_refresh_token_by_client_id(
            db=db, client_id=db_refresh_token.client_id
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "The provided refresh token has expired",
            },
        )

    if tokenreq.client_id is None:
        logger.warning(
            f"Token refresh_token_grant: Unprovided client_id ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_client",
                "error_description": "Invalid client_id or secret",
            },
        )

    auth_client: Type[BaseAuthClient] | None = settings.KNOWN_AUTH_CLIENTS.get(
        tokenreq.client_id
    )

    if auth_client is None:
        logger.warning(
            f"Token authorization_code_grant: Invalid client_id {tokenreq.client_id} ({request_id})"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_client",
                "error_description": "Invalid client id or secret",
            },
        )

    # If the auth provider expect to use a client secret, we don't use PKCE
    elif auth_client.secret is not None:
        # We need to check the correct client_secret was provided
        if auth_client.secret != tokenreq.client_secret:
            logger.warning(
                f"Token authorization_code_grant: Invalid secret for client {tokenreq.client_id} ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_client",
                    "error_description": "Invalid client id or secret",
                },
            )
    else:
        # We use PKCE, a client secret should not have been provided
        if tokenreq.client_secret is not None:
            logger.warning(
                f"Token authorization_code_grant: With PKCE, a client secret should not have been provided ({request_id})"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_client",
                    "error_description": "Invalid client id or secret",
                },
            )

    # If everything is good we can finally create the new access/refresh tokens
    # We use new refresh tokens every times as we use some client that can't store secrets (see Refresh token rotation in https://www.pingidentity.com/en/resources/blog/post/refresh-token-rotation-spa.html)
    # We use automatique reuse detection to prevent from replay attacks (https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)

    refresh_token = generate_token()
    new_db_refresh_token = models_auth.RefreshToken(
        token=refresh_token,
        client_id=db_refresh_token.client_id,
        created_on=datetime.now(),
        user_id=db_refresh_token.user_id,
        expire_on=datetime.now()
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        scope=db_refresh_token.scope,
    )
    await cruds_auth.create_refresh_token(db=db, db_refresh_token=new_db_refresh_token)

    response_body = create_response_body(
        db_refresh_token, tokenreq.client_id, refresh_token, settings, request_id
    )

    # Required headers by Oauth and oidc
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response_body


def create_response_body(db_row, client_id, refresh_token, settings):
    # We create a list of all the scopes we accept to grant to the user. These scopes will be included in the access token.
    # If API was provided in the request scope, we grant it
    # If it is an oidc request, we grant userinfos
    granted_scopes_list = []

    if db_row.scope is not None:
        if ScopeType.API in db_row.scope:
            granted_scopes_list.append(ScopeType.API)
        if ScopeType.openid in db_row.scope:
            granted_scopes_list.append(ScopeType.openid)

    granted_scopes = " ".join(granted_scopes_list)

    # TODO: is the client_id=aud really logic ? It is for oidc but for the access token i don't know
    access_token_data = schemas_auth.TokenData(
        sub=db_row.user_id, scopes=granted_scopes, aud=client_id
    )

    # Expiration date is included by `create_access_token` function
    access_token = create_access_token(data=access_token_data, settings=settings)

    id_token = None  # Will change if oidc is asked in scopes

    # Perform specifics steps for openid connect
    if db_row.scope is not None and "openid" in db_row.scope:
        # It's an openid connect request, we also need to return an `id_token`

        # The id_token is a JWS: a signed JWT
        # https://openid.net/specs/openid-connect-core-1_0.html#IDToken
        # It must contain the following claims:
        # * iss: the issuer value. Must be the same as the one provided in the discovery endpoint. Should be an url.
        # * sub: the subject identifier.
        # * aud: the audience. Must be the client client_id.
        # * exp: expiration datetime. Added by the function
        # * iat: Time at which the JWT was issued.
        # * if provided, nonce

        # For Nextcloud:
        # Required iss : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
        # Required claims : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016

        # id_token_data = {
        #    "iss": AUTH_ISSUER,
        #    "sub": db_row.user_id,
        #    "aud": client_id,
        #    # "exp"included by the function
        # }
        id_token_data = schemas_auth.TokenData(
            iss=settings.AUTH_ISSUER,
            sub=db_row.user_id,
            aud=client_id,
        )
        if db_row.nonce is not None:
            # oidc only, required if provided by the client
            id_token_data.nonce = db_row.nonce

        id_token = create_access_token_RS256(data=id_token_data, settings=settings)
        print("Token", id_token)

    # We create an OAuth response, with oidc specific elements if required
    response_body = schemas_auth.TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        scopes=granted_scopes,
        refresh_token=refresh_token,
        id_token=id_token,
    )

    return response_body


@router.get(
    "/auth/userinfo",
    tags=[Tags.auth],
)
async def auth_get_userinfo(
    request: Request,
    user: models_core.CoreUser = Depends(
        get_user_from_token_with_scopes([ScopeType.openid])
    ),
    token_data: schemas_auth.TokenData = Depends(get_token_data),
    settings: Settings = Depends(get_settings),
):  # productId: int = Body(...)):  # , request: Request):
    # access_token = authorization

    # The client_id is contained in aud field
    client_id = token_data.aud

    if client_id is None:
        raise HTTPException(
            status_code=401,
            detail="Unknown client_id",
        )

    auth_client = settings.KNOWN_AUTH_CLIENTS[client_id]
    auth_client.get_userinfo(user)

    return auth_client.get_userinfo(user=user)


@router.get(
    "/oidc/authorization-flow/jwks_uri",
    tags=[Tags.auth],
)
def jwks_uri(
    settings: Settings = Depends(get_settings),
):
    return settings.RSA_PUBLIC_JWK


@router.get(
    "/.well-known/openid-configuration",
    tags=[Tags.auth],
)
async def oidc_configuration(
    settings: Settings = Depends(get_settings),
):
    # See https://ldapwiki.com/wiki/Openid-configuration
    return {
        "issuer": settings.AUTH_ISSUER,
        "authorization_endpoint": settings.CLIENT_URL + "auth/authorize",
        "token_endpoint": settings.DOCKER_URL + "auth/token",
        "userinfo_endpoint": settings.DOCKER_URL + "auth/userinfo",
        "jwks_uri": settings.DOCKER_URL + "oidc/authorization-flow/jwks_uri",
        # RECOMMENDED The OAuth 2.0 / OpenID Connect URL of the OP's Dynamic Client Registration Endpoint OpenID.Registration.
        # TODO: is this relevant?
        # "registration_endpoint": "https://a/register",
        "request_parameter_supported": True,
        # TODO: what do we put? All scopes can be used with custom auth_provider class.
        # Do we put basic scopes that are always supported or do we concatenate all available scopes
        "scopes_supported": [
            "profile",
            "openid",
            "email",
            "address",
            "phone",
            "offline_access",
        ],
        # REQUIRED Must be code as wa only support authorization code grant
        "response_types_supported": [
            "code",
        ],
        "grant_types_supported": [
            "authorization_code",
        ],
        # https://openid.net/specs/openid-connect-core-1_0.html#SubjectIDTypes
        "subject_types_supported": [
            "public",
        ],
        "id_token_signing_alg_values_supported": [
            "RS256",
        ],
        # We don't support encrypted JWT : JWE
        # "id_token_encryption_alg_values_supported": [],
        # We don't support returning userinfo as an encrypted or a signed JWT
        # "userinfo_signing_alg_values_supported": [],
        # "userinfo_encryption_alg_values_supported": [],
        # "userinfo_encryption_enc_values_supported": [],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "none",  # When using PKCE there may be no client secret provided
        ],
        "claim_types_supported": ["normal"],
        # TODO: note: claims may depend/be extended using auth providers class
        "claims_supported": [
            "sub",
            "name",
            "preferred_username",
            "given_name",
            "family_name",
            "middle_name",
            "nickname",
            "profile",
            "picture",
            "website",
            "gender",
            "zone_info",
            "locale",
            "updated_time",
            "birthdate",
            "email",
            "email_verified",
            "phone_number",
            "address",
        ],
        # TODO: do we want to expose a documentation?
        # "service_documentation": "https://d/about",
        "claims_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        # TODO: add
        # The privacy policy document URL, omitted if none.
        # op_policy_uri = ""
        # The terms of service document URL, omitted if none.
        # op_tos_uri = ""
    }

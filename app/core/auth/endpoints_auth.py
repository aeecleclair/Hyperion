import base64
import hashlib
import logging
import urllib.parse
from datetime import UTC, datetime, timedelta

import calypsso
import jwt
from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import cruds_auth, models_auth, schemas_auth
from app.core.users import cruds_users, models_users
from app.core.utils.config import Settings
from app.core.utils.security import (
    authenticate_user,
    create_access_token,
    create_access_token_RS256,
    generate_token,
    jws_algorithm,
    jwt_algorithm,
)
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    get_token_data,
    get_user_from_token_with_scopes,
)
from app.types.exceptions import AuthHTTPException
from app.types.module import CoreModule
from app.types.scopes_type import ScopeType
from app.utils.auth.providers import BaseAuthClient
from app.utils.tools import has_user_permission

router = APIRouter(tags=["Auth"])

core_module = CoreModule(
    root="auth",
    tag="Auth",
    router=router,
    factory=None,
)

# We could maybe use hyperion.security
hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_security_logger = logging.getLogger("hyperion.security")


# WARNING: if new flow are added, openid_config should be updated accordingly


# TODO: maybe remove
@router.post(
    "/auth/simple_token",
    response_model=schemas_auth.AccessToken,
    status_code=200,
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
    data = schemas_auth.TokenData(sub=user.id, scopes=ScopeType.auth)
    access_token = create_access_token(settings=settings, data=data)
    return {"access_token": access_token, "token_type": "bearer"}


# Authorization Code Grant #

# Terminology:
# Authorization Code Grant: a type of oauth flow. Useful for server served webapp or mobile app
# Client: the entity which want to get an authorization to some resources from the resource server owned by a user
# Resource server: the entity that can serve resources in exchange for a token, ex: a user profile. Here it's Hyperion
# Authorization server: the entity that is in charge of authorization. Using an oauth flow, it will give tokens.

# https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/
# https://www.oauth.com/oauth2-servers/server-side-apps/example-flow/


# Authentication Request
# Common to OAuth 2.0 and OIDC


@router.get(
    "/auth/authorize",
    response_class=HTMLResponse,
)
async def get_authorize_page(
    # The parameters should be passed as query strings. We need to use Depends() for that as we want to put them in a schema
    authorizereq: schemas_auth.Authorize = Depends(),
    settings: Settings = Depends(get_settings),
):
    """
    This endpoint is the one the user is redirected to when they begin the Oauth or Openid connect (*oidc*) *Authorization code* process.
    The page allows the user to login and may let the user choose what type of data they want to authorize the client for.

    This is the endpoint that should be set in the client OAuth or OIDC configuration page. It can be called by a GET or a POST request.

    See `/auth/authorization-flow/authorize-validation` endpoint for information about the parameters.

    > In order for the authorization code grant to be secure, the authorization page must appear in a web browser the user is familiar with,
    > and must not be embedded in an iframe popup or an embedded browser in a mobile app.
    > If it could be embedded in another website, the user would have no way of verifying it is the legitimate service and is not a phishing attempt.

    **This endpoint is a UI endpoint which send and html page response. It will redirect to `/auth/authorization-flow/authorize-validation`**
    """

    return RedirectResponse(
        settings.CLIENT_URL
        + calypsso.get_login_relative_url(**authorizereq.model_dump()),
        status_code=status.HTTP_302_FOUND,
    )


@router.post(
    "/auth/authorize",
    response_class=HTMLResponse,
)
async def post_authorize_page(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str | None = Form(None),
    state: str | None = Form(None),
    nonce: str | None = Form(None),
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form(None),
    settings: Settings = Depends(get_settings),
):
    """
    This endpoint is the one the user is redirected to when they begin the OAuth or Openid connect (*oidc*) *Authorization code* process with or without PKCE.
    The page allows the user to login and may let the user choose what type of data they want to authorize the client for.

    This is the endpoint that should be set in the client OAuth or OIDC configuration page. It can be called by a GET or a POST request.

    See `/auth/authorization-flow/authorize-validation` endpoint for information about the parameters.

    > In order for the authorization code grant to be secure, the authorization page must appear in a web browser the user is familiar with,
    > and must not be embedded in an iframe popup or an embedded browser in a mobile app.
    > If it could be embedded in another website, the user would have no way of verifying it is the legitimate service and is not a phishing attempt.

    **This endpoint is a UI endpoint which send and html page response. It will redirect to `/auth/authorization-flow/authorize-validation`**
    """

    return RedirectResponse(
        settings.CLIENT_URL
        + calypsso.get_login_relative_url(
            response_type=response_type,
            redirect_uri=redirect_uri,
            client_id=client_id,
            scope=scope,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        ),
        status_code=status.HTTP_302_FOUND,
    )


@router.post(
    "/auth/authorization-flow/authorize-validation",
    response_class=RedirectResponse,
)
async def authorize_validation(
    # User validation
    authorizereq: schemas_auth.AuthorizeValidation = Depends(
        schemas_auth.AuthorizeValidation.as_form,
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
    # Note: we may want to add a window to let the user choose which scopes they grant access to.

    hyperion_access_logger.info(
        f"Authorize-validation: Starting for client {authorizereq.client_id} ({request_id})",
    )

    # Check if the client is registered in the server. auth_client will be None if the client_id is not known.
    auth_client: BaseAuthClient | None = settings.KNOWN_AUTH_CLIENTS.get(
        authorizereq.client_id,
    )
    if auth_client is None:
        # The client does not exist
        hyperion_access_logger.warning(
            f"Authorize-validation: Invalid client_id {authorizereq.client_id}. Is `AUTH_CLIENTS` variable correctly configured in the dotenv? ({request_id})",
        )
        return RedirectResponse(
            settings.CLIENT_URL
            + calypsso.get_message_relative_url(
                message_type=calypsso.TypeMessage.invalid_client_id,
            ),
            status_code=status.HTTP_302_FOUND,
        )

    # The auth_client allows to override the redirect_uri and bypass related verifications
    # This behaviour is not part of OAuth or Openid connect specifications
    if auth_client.override_redirect_uri is not None:
        hyperion_access_logger.info(
            f"Authorize-validation: Overriding redirect_uri with {auth_client.override_redirect_uri}, as configured in the auth client ({request_id})",
        )
        redirect_uri = auth_client.override_redirect_uri
    # If at least one redirect_uri is hardcoded in the auth_client we will use this one. If one was provided in the request, we want to make sure they match.
    elif authorizereq.redirect_uri is None:
        # We use the hardcoded value
        redirect_uri = auth_client.redirect_uri[0]
    # If a redirect_uri is provided, it should match one specified in the auth client
    elif authorizereq.redirect_uri not in auth_client.redirect_uri:
        hyperion_access_logger.warning(
            f"Authorize-validation: Mismatching redirect_uri, received {authorizereq.redirect_uri} but expected one of {auth_client.redirect_uri} ({request_id})",
        )
        return RedirectResponse(
            settings.CLIENT_URL
            + calypsso.get_message_relative_url(
                message_type=calypsso.TypeMessage.mismatching_redirect_uri,
            ),
            status_code=status.HTTP_302_FOUND,
        )
    else:
        redirect_uri = authorizereq.redirect_uri

    # Special characters like `:` or `/` may be encoded as `%3A` and `%2F`, we need to decode them before returning the redirection object
    redirect_uri = urllib.parse.unquote(redirect_uri)

    # Currently, `code` is the only flow supported
    if authorizereq.response_type != "code":
        hyperion_access_logger.warning(
            f"Authorize-validation: Unsupported response_type, received {authorizereq.response_type} ({request_id})",
        )
        url = redirect_uri + "?error=" + "unsupported_response_type"
        if authorizereq.state:
            url += "&state=" + authorizereq.state
        return RedirectResponse(url, status_code=status.HTTP_302_FOUND)

    # TODO: Currently if the user enters the wrong credentials in the form, they won't be redirected to the login page again but the OAuth process will fail.
    user = await authenticate_user(db, authorizereq.email, authorizereq.password)
    if not user:
        hyperion_access_logger.warning(
            f"Authorize-validation: Invalid user email or password for email {authorizereq.email} ({request_id})",
        )
        return RedirectResponse(
            settings.CLIENT_URL
            + calypsso.get_login_relative_url(
                **authorizereq.model_dump(exclude={"email", "password"}),
                credentials_error=True,
            ),
            status_code=status.HTTP_302_FOUND,
        )

    # The auth_client may restrict the usage of the client to specific Hyperion permissions
    if auth_client.permission is not None:
        if not (
            await has_user_permission(
                user=user,
                permission_name=auth_client.permission,
                db=db,
            )
        ):
            hyperion_access_logger.warning(
                f"Authorize-validation: user is not member of an allowed group {authorizereq.email} ({request_id})",
            )
            return RedirectResponse(
                settings.CLIENT_URL
                + calypsso.get_message_relative_url(
                    message_type=calypsso.TypeMessage.user_not_member_of_allowed_group,
                ),
                status_code=status.HTTP_302_FOUND,
            )

    # We generate a new authorization_code
    # The authorization code MUST expire
    # shortly after it is issued to mitigate the risk of leaks. A
    # maximum authorization code lifetime of 10 minutes is
    # RECOMMENDED. The client MUST NOT use the authorization code more than once.
    authorization_code = generate_token()
    expire_on = datetime.now(UTC) + timedelta(
        minutes=settings.AUTHORIZATION_CODE_EXPIRE_MINUTES,
    )
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
        db=db,
        db_authorization_code=db_authorization_code,
    )

    # We need to redirect to the `redirect_uri` provided by the *client* providing the new authorization_code.
    # For security reason, we need to provide the same `state` and `nonce` if they were provided by the client in the first request
    url = redirect_uri + "?code=" + authorization_code
    if authorizereq.state:
        url += "&state=" + authorizereq.state
    # We need to redirect the user with as a GET request.
    # By default, RedirectResponse send a 307 code, which prevent the user browser from changing the POST of this endpoint to a GET
    # We specifically return a 302 code to allow the user browser to change the POST of this endpoint to a GET
    # See https://stackoverflow.com/a/65512571
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/auth/token",
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
    The client exchange its authorization code for an access token. The endpoint supports OAuth and Openid connect, with or without PKCE.

    Parameters must be `application/x-www-form-urlencoded` and include:

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

    hyperion_access_logger.info(
        f"Token: Starting {tokenreq.grant_type} grant for client {tokenreq.client_id} ({request_id})",
    )

    if tokenreq.grant_type == "authorization_code":
        return await authorization_code_grant(
            db=db,
            settings=settings,
            tokenreq=tokenreq,
            response=response,
            request_id=request_id,
        )

    if tokenreq.grant_type == "refresh_token":
        return await refresh_token_grant(
            db=db,
            settings=settings,
            tokenreq=tokenreq,
            response=response,
            request_id=request_id,
        )

    hyperion_access_logger.warning(
        f"Token: Unsupported grant_type, received {tokenreq.grant_type} ({request_id})",
    )
    raise AuthHTTPException(
        status_code=400,
        error="unsupported_grant_type",
        error_description=f"{tokenreq.grant_type} is not supported",
    )


async def authorization_code_grant(
    db: AsyncSession,
    settings: Settings,
    tokenreq: schemas_auth.TokenReq,
    response: Response,
    request_id: str,
):
    if tokenreq.code is None:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Unprovided authorization code ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="An authorization code should be provided",
        )

    # We need to check that the authorization code that was provided in the request is the one that was previously saved in the database
    db_authorization_code = await cruds_auth.get_authorization_token_by_token(
        db=db,
        code=tokenreq.code,
    )
    if db_authorization_code is None:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Invalid authorization code ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="The provided authorization code is invalid",
        )

    # The authorization code should only be usable once
    # We want to remove it from the database even if the request fail.
    # That's why we delete it at the beginning of this function
    await cruds_auth.delete_authorization_token_by_token(db=db, code=tokenreq.code)

    if tokenreq.client_id is None:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Unprovided client_id ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_client",
            error_description="Invalid client_id or secret",
        )

    auth_client: BaseAuthClient | None = settings.KNOWN_AUTH_CLIENTS.get(
        tokenreq.client_id,
    )

    if auth_client is None:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Invalid client_id {tokenreq.client_id}. Is `AUTH_CLIENTS` variable correctly configured in the dotenv? ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_client",
            error_description="Invalid client id or secret",
        )

    if auth_client.secret is not None:
        pass
        # As PKCE is not used, we need to make sure that PKCE related parameters were not used
        # 04/02/2025: As a hotfix, we allow all clients to use PKCE with a client secret
        # if (
        #     db_authorization_code.code_challenge is not None
        #     or tokenreq.code_verifier is not None
        # ):
        # We allow some auth clients to bypass this verification
        # because some auth providers may use PKCE with a client secret event if it's forbidden by the specifications
        # if not auth_client.allow_pkce_with_client_secret:
        #     hyperion_access_logger.warning(
        #         f"Token authorization_code_grant: PKCE related parameters should not be used when using a client secret ({request_id})",
        #     )
        #     raise AuthHTTPException(
        #         status_code=400,
        #         error="invalid_request",
        #         error_description="PKCE related parameters should not be used",
        #     )
    elif (
        db_authorization_code.code_challenge is not None
        and tokenreq.code_verifier is not None
    ):
        # We use PKCE
        pass
    else:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Client must provide a client_secret or a code_verifier ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="Client must provide a client_secret or a code_verifier",
        )

    # Then we verify passed client_secret or code_verifier are valid

    # If the auth provider expect to use a client secret, we verify it
    if auth_client.secret is not None:
        # We need to check the correct client_secret was provided
        if auth_client.secret != tokenreq.client_secret:
            hyperion_access_logger.warning(
                f"Token authorization_code_grant: Invalid secret for client {tokenreq.client_id} ({request_id})",
            )
            raise AuthHTTPException(
                status_code=400,
                error="invalid_client",
                error_description="Invalid client id or secret",
            )

    # If we use PKCE, we need to verify the code_verifier
    if (
        db_authorization_code.code_challenge is not None
        and tokenreq.code_verifier is not None
    ):
        # We need to verify the hash correspond
        # The hash is a H256, urlbase64 encoded
        # If the last character is not a "=", we need to add it, as the = is optional for urlbase64 encoding
        code_challenge = db_authorization_code.code_challenge
        if code_challenge[-1] != "=":
            code_challenge += "="
        if (
            code_challenge.encode()
            != base64.urlsafe_b64encode(
                hashlib.sha256(tokenreq.code_verifier.encode()).digest(),
            )
            # We need to pass the code_verifier as a b-string, we use `code_verifier.encode()` for that
            # TODO: Make sure that `.hexdigest()` is applied by the client to code_challenge
        ):
            hyperion_access_logger.warning(
                f"Token authorization_code_grant: Invalid code_verifier ({request_id})",
            )
            raise AuthHTTPException(
                status_code=400,
                error="invalid_request",
                error_description="Invalid code_verifier",
            )

    # We can check the authorization code
    if db_authorization_code.expire_on < datetime.now(UTC):
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Expired authorization code ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="Expired authorization code",
        )

    # The auth_client allows to override the redirect_uri and bypass related verifications
    # This behaviour is not part of OAuth or Openid connect specifications
    if auth_client.override_redirect_uri is not None:
        tokenreq.redirect_uri = auth_client.override_redirect_uri
    # A redirect_uri may be hardcoded in the client
    elif auth_client.redirect_uri is not None:
        if tokenreq.redirect_uri is None:
            # We use the hardcoded value
            tokenreq.redirect_uri = auth_client.redirect_uri[0]
        # If a redirect_uri is provided, it should match one specified in the auth client
        if tokenreq.redirect_uri not in auth_client.redirect_uri:
            hyperion_access_logger.warning(
                f"Token authorization_code_grant: redirect_uri {tokenreq.redirect_uri} do not match hardcoded redirect_uri ({request_id})",
            )
            raise AuthHTTPException(
                status_code=400,
                error="invalid_request",
                error_description="redirect_uri does not match",
            )

    # If a redirect_uri was provided in the previous request, we need to check they match
    # > Ensure that the redirect_uri parameter value is identical to the redirect_uri parameter value that was included in the initial Authorization Request.
    # > If the redirect_uri parameter value is not present when there is only one registered redirect_uri value, the Authorization Server MAY return an error (since the Client should have included the parameter) or MAY proceed without an error (since OAuth 2.0 permits the parameter to be omitted in this case).
    # If a redirect_uri is provided, it should match the one in the auth client
    if tokenreq.redirect_uri != db_authorization_code.redirect_uri:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: redirect_uri {tokenreq.redirect_uri} do not match the redirect_uri provided previously {db_authorization_code.redirect_uri} ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="redirect_uri should remain identical",
        )

    refresh_token = generate_token()
    new_db_refresh_token = models_auth.RefreshToken(
        token=refresh_token,
        client_id=tokenreq.client_id,
        created_on=datetime.now(UTC),
        user_id=db_authorization_code.user_id,
        expire_on=datetime.now(UTC)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        scope=db_authorization_code.scope,
        nonce=db_authorization_code.nonce,
    )
    await cruds_auth.create_refresh_token(db=db, db_refresh_token=new_db_refresh_token)

    response_body = await create_response_body(
        db_authorization_code,
        tokenreq.client_id,
        refresh_token,
        auth_client,
        settings,
        request_id,
        db,
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
        hyperion_access_logger.warning(
            f"Token refresh_token_grant: refresh_token was not provided ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="refresh_token is required",
        )

    db_refresh_token = await cruds_auth.get_refresh_token_by_token(
        db=db,
        token=tokenreq.refresh_token,
    )

    if db_refresh_token is None:
        hyperion_access_logger.warning(
            f"Token refresh_token_grant: invalid refresh token ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="Invalid refresh token",
        )
    if db_refresh_token.revoked_on is not None:
        # If the client tries to use a revoked refresh_token, we want to revoke all other refresh tokens from this client and user
        await cruds_auth.revoke_refresh_token_by_client_and_user_id(
            db=db,
            client_id=db_refresh_token.client_id,
            user_id=db_refresh_token.user_id,
        )
        hyperion_security_logger.warning(
            f"Tentative to use a revoked refresh token ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="The provided refresh token has been revoked",
        )

    await cruds_auth.revoke_refresh_token_by_token(db=db, token=tokenreq.refresh_token)

    if db_refresh_token.expire_on < datetime.now(UTC):
        await cruds_auth.revoke_refresh_token_by_token(
            db=db,
            token=db_refresh_token.token,
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_request",
            error_description="The provided refresh token has expired",
        )

    if tokenreq.client_id is None:
        hyperion_access_logger.warning(
            f"Token refresh_token_grant: Unprovided client_id ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_client",
            error_description="Invalid client_id or secret",
        )

    auth_client: BaseAuthClient | None = settings.KNOWN_AUTH_CLIENTS.get(
        tokenreq.client_id,
    )

    if auth_client is None:
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: Invalid client_id {tokenreq.client_id} ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_client",
            error_description="Invalid client id or secret",
        )

    # If the auth provider expects to use a client secret, we don't use PKCE
    if auth_client.secret is not None:
        # We need to check the correct client_secret was provided
        if auth_client.secret != tokenreq.client_secret:
            hyperion_access_logger.warning(
                f"Token authorization_code_grant: Invalid secret for client {tokenreq.client_id} ({request_id})",
            )
            raise AuthHTTPException(
                status_code=400,
                error="invalid_client",
                error_description="Invalid client id or secret",
            )
    elif tokenreq.client_secret is not None:
        # We use PKCE, a client secret should not have been provided
        hyperion_access_logger.warning(
            f"Token authorization_code_grant: With PKCE, a client secret should not have been provided ({request_id})",
        )
        raise AuthHTTPException(
            status_code=400,
            error="invalid_client",
            error_description="Invalid client id or secret",
        )

    # If everything is good we can finally create the new access/refresh tokens
    # We use new refresh tokens every time as we use some client that can't store secrets (see Refresh token rotation in https://www.pingidentity.com/en/resources/blog/post/refresh-token-rotation-spa.html)
    # We use automatic reuse detection to prevent from replay attacks (https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)

    refresh_token = generate_token()
    new_db_refresh_token = models_auth.RefreshToken(
        token=refresh_token,
        client_id=db_refresh_token.client_id,
        created_on=datetime.now(UTC),
        user_id=db_refresh_token.user_id,
        expire_on=datetime.now(UTC)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        scope=db_refresh_token.scope,
    )
    await cruds_auth.create_refresh_token(db=db, db_refresh_token=new_db_refresh_token)

    response_body = await create_response_body(
        db_refresh_token,
        tokenreq.client_id,
        refresh_token,
        auth_client,
        settings,
        request_id,
        db,
    )

    # Required headers by Oauth and oidc
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response_body


async def create_response_body(
    db_row: models_auth.AuthorizationCode | models_auth.RefreshToken,
    client_id: str,
    refresh_token: str,
    auth_client: BaseAuthClient,
    settings: Settings,
    request_id: str,
    db: AsyncSession,
):
    # In the request, the client ask for some scopes. The auth provider decides which scopes he grants to the client.

    # We have a space separated string of requested scopes : db_row.scope
    # We use a set representation as:
    #  - scopes should be unique
    #  - we will intersect requested scopes with allowed scopes, which is an easier operation with a set than a list
    requested_scopes_set: set[str] = set((db_row.scope or "").split(" "))

    # We create a list of all the scopes we accept to grant to the user to include them in the access token.

    granted_scopes_set: set[ScopeType | str] = auth_client.filter_scopes(
        requested_scopes=requested_scopes_set,
    )
    refused_scopes = requested_scopes_set - granted_scopes_set
    if refused_scopes:
        hyperion_security_logger.warning(
            f"Token authorization_code_grant: Refused scopes {refused_scopes} for client {client_id} ({request_id})",
        )

    granted_scopes = " ".join(granted_scopes_set)

    hyperion_access_logger.warning(
        f"Token create_response_body: Granting scopes {granted_scopes} ({request_id})",
    )

    # The audience field should be the name of the service the access token gives access to
    # For the access token, it's always the API. We decide not to include this field as we know we are the one who issued the access token
    # For the id token, it's the service which will use it, we thus need to include aud=client_id
    # In order to be able to identify the client using the access token we may add a public claim `cid=client_id`, see bellow
    access_token_data = schemas_auth.TokenData(
        sub=db_row.user_id,
        scopes=granted_scopes,
    )

    id_token = None  # Will change if oidc is asked in scopes

    if ScopeType.profile in granted_scopes_set:
        # We add the cid in the access token to be able to access the userinfo endpoint (openid norm)
        access_token_data.cid = client_id

    # Perform specifics steps for openid connect
    if ScopeType.openid in granted_scopes_set:
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

        # exp is set by the token creation function
        # aud=client_id as it's the client verify the id_token
        id_token_data = schemas_auth.TokenData(
            iss=settings.OIDC_ISSUER,
            sub=db_row.user_id,
            aud=client_id,
        )
        if db_row.nonce is not None:
            # parameter for oidc only, required if provided by the client
            id_token_data.nonce = db_row.nonce

        # In order to provide the user information in a format understandable by the client, we need to be able to identify it
        # For that, we include a public cid claim in the access token
        access_token_data.cid = client_id

        # Some rare oidc providers (like NextAuth.js) does not support getting userinfo from userinfo endpoints
        # but instead require to include the user information in the id_token
        additional_data = {}
        if auth_client.return_userinfo_in_id_token:
            user = await cruds_users.get_user_by_id(db=db, user_id=db_row.user_id)
            if user is None:
                hyperion_security_logger.error(
                    f"Create oidc response body: Could not find user {db_row.user_id} when trying the get userinfo but it should exist ({request_id})",
                )
                raise HTTPException(
                    status_code=500,
                    detail="Could not find user when trying the get userinfo but it should exist",
                )
            additional_data = auth_client.get_userinfo(user=user)

        id_token = create_access_token_RS256(
            data=id_token_data,
            additional_data=additional_data,
            settings=settings,
        )

    # Expiration date is included by `create_access_token` function
    access_token = create_access_token(data=access_token_data, settings=settings)

    # We create an OAuth response, with oidc specific elements if required
    return schemas_auth.TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        scope=granted_scopes,
        refresh_token=refresh_token,
        id_token=id_token,
    )


@router.post(
    "/auth/introspect",
    response_model=schemas_auth.IntrospectTokenResponse,
    status_code=200,
)
async def introspect(
    response: Response,
    # OAuth and Openid connect parameters
    # The client id and secret must be passed either in the authorization header or with client_id and client_secret parameters
    tokenreq: schemas_auth.IntrospectTokenReq = Depends(
        schemas_auth.IntrospectTokenReq.as_form,
    ),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Some clients requires an endpoint to check if an access token or a refresh token is valid.
    This endpoint should not be publicly accessible, and is thus restricted to some AuthClient.

    * parameters:
        * `token`: the token to introspect
        * `token_type_hint`: may be `access_token` or `refresh_token`, we currently do not use this hint as we are able to differentiate access and refresh tokens

    * Client credentials
        The client must send either:
            the client id and secret in the authorization header or with client_id and client_secret parameters

    Reference:
    https://www.oauth.com/oauth2-servers/token-introspection-endpoint/
    https://datatracker.ietf.org/doc/html/rfc7662
    """
    # We need to check client id and secret
    if authorization is not None:
        # client_id and client_secret are base64 encoded in the Basic authorization header
        tokenreq.client_id, tokenreq.client_secret = (
            base64.b64decode(authorization.replace("Basic ", ""))
            .decode("utf-8")
            .split(":")
        )

    if tokenreq.client_id is None:
        hyperion_access_logger.warning(
            f"Token introspection: Unprovided client_id ({request_id})",
        )
        raise HTTPException(
            status_code=401,
            detail="Unprovided client_id",
        )

    auth_client: BaseAuthClient | None = settings.KNOWN_AUTH_CLIENTS.get(
        tokenreq.client_id,
    )

    if (
        auth_client is None
        or auth_client.secret is None
        or tokenreq.client_secret != auth_client.secret
    ):
        hyperion_access_logger.warning(
            f"Token introspection: Invalid client_id {tokenreq.client_id} or secret. Token introspection is not supported without a client secret. Is `AUTH_CLIENTS` variable correctly configured in the dotenv? ({request_id})",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid client_id or client_secret",
        )

    if not auth_client.allow_token_introspection:
        hyperion_access_logger.warning(
            f"Token introspection: Token introspection is not supported for client {tokenreq.client_id} ({request_id})",
        )
        raise HTTPException(
            status_code=401,
            detail="Token introspection is not supported for this client",
        )

    if len(tokenreq.token.split(".")) == 3:
        # This should be an access JWT token
        return introspect_access_token(access_token=tokenreq.token, settings=settings)

    # This should be a an urlsafe refresh token generated using `generate_token`
    return await introspect_refresh_token(refresh_token=tokenreq.token, db=db)


def introspect_access_token(
    access_token: str,
    settings: Settings,
) -> schemas_auth.IntrospectTokenResponse:
    try:
        payload = jwt.decode(
            access_token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[jwt_algorithm],
        )
        # We want to validate the structure of the payload
        _ = schemas_auth.TokenData(**payload)
        return schemas_auth.IntrospectTokenResponse(active=True)
    except Exception:
        return schemas_auth.IntrospectTokenResponse(active=False)


async def introspect_refresh_token(
    refresh_token: str,
    db: AsyncSession,
) -> schemas_auth.IntrospectTokenResponse:
    db_refresh_token = await cruds_auth.get_refresh_token_by_token(
        db=db,
        token=refresh_token,
    )

    if db_refresh_token is None:
        # The refresh token is invalid
        return schemas_auth.IntrospectTokenResponse(active=False)
    if db_refresh_token.revoked_on is not None:
        # The refresh token was already revoked
        return schemas_auth.IntrospectTokenResponse(active=False)
    if db_refresh_token.expire_on < datetime.now(UTC):
        # The refresh token is expired
        return schemas_auth.IntrospectTokenResponse(active=False)

    return schemas_auth.IntrospectTokenResponse(active=True)


@router.get(
    "/auth/userinfo",
    status_code=200,
)
async def auth_get_userinfo(
    user: models_users.CoreUser = Depends(
        get_user_from_token_with_scopes([[ScopeType.openid], [ScopeType.profile]]),
    ),
    token_data: schemas_auth.TokenData = Depends(get_token_data),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Openid connect specify an endpoint the client can use to get information about the user.
    The oidc client will provide the access_token it got previously in the request.

    The information expected depends on the client and may include the user identifier, name, email, phone...
    See the reference for possible claims. See the client documentation and implementation to know what it needs and can receive.
    The sub (subject) Claim MUST always be returned in the UserInfo Response.

    The client can ask for specific information using scopes and claims. See the reference for more information.
    This procedure is not implemented in Hyperion as we can customize the response using auth_client class

    Reference:
    https://openid.net/specs/openid-connect-core-1_0.html#UserInfo
    """

    # For openid connect, the client_id is added in the public cid field
    client_id = token_data.cid

    if client_id is None:
        hyperion_access_logger.warning(
            f"User info: Unprovided client_id ({request_id})",
        )
        raise HTTPException(
            status_code=401,
            detail="Unprovided client_id",
        )

    auth_client: BaseAuthClient | None = settings.KNOWN_AUTH_CLIENTS.get(client_id)

    if auth_client is None:
        hyperion_access_logger.warning(
            f"User info: Invalid client_id {client_id}. Is `AUTH_CLIENTS` variable correctly configured in the dotenv? ({request_id})",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid client_id",
        )

    return auth_client.get_userinfo(user=user)


@router.get(
    "/oidc/authorization-flow/jwks_uri",
)
def jwks_uri(
    settings: Settings = Depends(get_settings),
):
    return settings.RSA_PUBLIC_JWK


@router.get(
    "/.well-known/oauth-authorization-server",
)
async def oauth_configuration(
    settings: Settings = Depends(get_settings),
):
    # See https://datatracker.ietf.org/doc/html/rfc8414
    return get_oidc_provider_metadata(settings)


@router.get(
    "/.well-known/openid-configuration",
)
async def oidc_configuration(
    settings: Settings = Depends(get_settings),
):
    # See https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata
    return get_oidc_provider_metadata(settings)


def get_oidc_provider_metadata(settings: Settings):
    overridden_client_url = (
        settings.OVERRIDDEN_CLIENT_URL_FOR_OIDC or settings.CLIENT_URL
    )
    return {
        "issuer": settings.OIDC_ISSUER,  # We want to remove the trailing slash
        "authorization_endpoint": settings.CLIENT_URL + "auth/authorize",
        "token_endpoint": overridden_client_url + "auth/token",
        "userinfo_endpoint": overridden_client_url + "auth/userinfo",
        "introspection_endpoint": overridden_client_url + "auth/introspect",
        "jwks_uri": overridden_client_url + "oidc/authorization-flow/jwks_uri",
        # RECOMMENDED The OAuth 2.0 / OpenID Connect URL of the OP's Dynamic Client Registration Endpoint OpenID.Registration.
        # TODO: is this relevant?
        # TODO: add for Calypsso
        # "registration_endpoint": "https://a/register",
        "request_parameter_supported": True,
        "scopes_supported": [scope.value for scope in ScopeType],
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
            jws_algorithm,
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
        # NOTE: claims may depend/be extended using auth providers class
        "claims_supported": [
            "sub",
            "name",
            "firstname",
            "nickname",
            "profile",
            "picture",
            "email",
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

import base64
import hashlib
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    authenticate_user,
    create_access_token,
    create_access_token_RS256,
    generate_token,
)
from app.cruds import cruds_auth
from app.dependencies import get_current_user, get_db
from app.models import models_core
from app.schemas import schemas_core
from app.utils.types.tags import Tags

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# @router.post(
#     "/auth/token",
#     response_model=schemas_core.AccessToken,
#     status_code=200,
#     tags=[Tags.auth],
# )
# async def login_for_access_token(
#     form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
# ):
#     """
#     Ask for a JWT access token using oauth password flow.

#     *username* and *password* must be provided

#     Note: the request body needs to use **form-data** and not json.
#     """
#     user = await authenticate_user(db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect login or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     # We put the user id in the subject field of the token.
#     # The subject `sub` is a JWT registered claim name, see https://datatracker.ietf.org/doc/html/rfc7519#section-4.1
#     access_token = create_access_token(data={"sub": user.id})
#     return {"access_token": access_token, "token_type": "bearer"}


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

# TODO: use a data class, or a SQL table
known_clients = {
    "application": {
        "secret": "secret",
        "redirect_uri": "http://localhost:8009/index.php/apps/oidc_login/oidc",
    },
    "myapplication": {
        "secret": "mysecret",
        "redirect_uri": "http://localhost:8000/auth/callback",
    },
}

AUTH_ISSUER = "hyperion"


@router.get(
    "/auth/authorize",
)
async def get_authorize_page(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None = None,
    state: str | None = None,
    nonce: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    db: AsyncSession = Depends(get_db),
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
    "/auth/authorize",
)
async def post_authorize_page(
    request: Request,
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str | None = Form(None),
    state: str | None = Form(None),
    nonce: str | None = Form(None),
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
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
)
async def authorize_validation(
    # We use Form(...) as parameters must be `application/x-www-form-urlencoded`
    request: Request,
    # User validation
    email: str = Form(...),
    password: str = Form(...),
    # OAuth and Openid connect parameters
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str | None = Form(None),
    scope: str | None = Form(None),
    state: str | None = Form(None),
    # Openid connect parameters only
    nonce: str | None = Form(None),
    # PKCE parameters
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form(None),
    # Database
    db: AsyncSession = Depends(get_db),
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

    * additional parameters for PKCE:
        * `code_challenge`: PKCE only
        * `code_challenge_method`: PKCE only


    * parameters that allows to authenticate the user and know which scopes he grants access to.
        * `email`
        * `password`

    Note: we may want to use a JWT here instead or email/password in order to be able to check if the user is already logged in.
    Note: we may want add a windows to let the user which scopes he grants access to.

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

    # Check if the client is registered in the server
    if client_id not in known_clients:
        # TODO: add error logging
        raise HTTPException(
            status_code=422,
            detail="Invalid client_id",
        )

    # If redirect_uri was not provided, use the one chosen during the client registration
    if redirect_uri is None:
        if known_clients[client_id]["redirect_uri"] is None:
            # TODO: add logging error
            raise HTTPException(
                status_code=422,
                detail="No redirect_uri were provided",
            )
        redirect_uri = known_clients[client_id]["redirect_uri"]

    # Check the provided redirect_uri is the same as the one chosen during the client registration (if it exists)
    if known_clients[client_id]["redirect_uri"] is not None:
        if redirect_uri != known_clients[client_id]["redirect_uri"]:
            # TODO: add logging error
            # raise HTTPException(
            #    status_code=422,
            #    detail="Redirect_uri do not math",
            # )
            # TODO
            print(
                "Warning, redirect uri do not match. Using the one provided by the client during the registration"
            )
            redirect_uri = known_clients[client_id]["redirect_uri"]

    # Currently, `code` is the only flow supported
    if response_type != "code":
        url = (
            redirect_uri.replace("%3A", ":").replace("%2F", "/")
            + "?error="
            + "unsupported_response_type"
        )
        if state:
            url += "&state=" + state
        return RedirectResponse(url)

    # TODO: replace the email/password by a JWT with an auth only scope.
    # Currently if the user enter the wrong credentials in the form, he won't be redirected to the login page again but the OAuth process will fail.
    user = await authenticate_user(db, email, password)
    if not user:
        # TODO: add logging
        url = (
            redirect_uri.replace("%3A", ":").replace("%2F", "/")
            + "?error="
            + "unsupported_response_type"
        )
        if state:
            url += "&state=" + state
        return RedirectResponse(url)

    # We generate a new authorization_code
    # The authorization code MUST expire
    # shortly after it is issued to mitigate the risk of leaks.  A
    # maximum authorization code lifetime of 10 minutes is
    # RECOMMENDED.  The client MUST NOT use the authorization code more than once.
    authorization_code = generate_token()
    expire_on = datetime.now() + timedelta(hours=1)
    # We save this authorization_code to the database
    # We can not use a JWT for this as:
    # - we need to store data about the OAuth/oidc request
    # - we need to invalidate the token after its utilisation
    # TODO: we need to remove the token from the db after its expiration
    db_authorization_code = models_core.AuthorizationCode(
        code=authorization_code,
        expire_on=expire_on,
        scope=scope,
        redirect_uri=redirect_uri,
        user_id=user.id,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    await cruds_auth.create_authorization_token(
        db=db, db_authorization_code=db_authorization_code
    )

    # We need to redirect to the `redirect_uri` provided by the *client* providing the new authorization_code.
    # For security reason, we need to provide the same `state` and `nonce` if they were provided by the client in the first request
    url = (
        redirect_uri.replace("%3A", ":").replace("%2F", "/")
        + "?code="
        + authorization_code
    )
    if state:
        url += "&state=" + state
    if nonce:
        url += "&nonce=" + nonce
    print("Redirecting to " + url)
    # We need to redirect the user with as a GET request.
    # By default RedirectResponse send a 307 code, which prevent the user browser from changing the POST of this endpoint to a GET
    # We specifically return a 302 code to allow the user browser to change the POST of this endpoint to a GET
    # See https://stackoverflow.com/a/65512571
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.post("/auth/token")
async def token(
    request: Request,
    response: Response,
    # OAuth and Openid connect parameters
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str | None = Form(None),
    # The client id and secret must be passed either in the authorization header or with client_id and client_secret parameters
    authorization: str | None = Header(default=None),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    # PKCE parameters
    code_verifier: str | None = Form(None),
    # Database
    db: AsyncSession = Depends(get_db),
):
    """
    Part 2 of the authorization code grant.
    The client exchange its authorization code for an access token. The endpoint support OAuth and Openid connect, with or without PKCE.

    Parameters must be `application/x-www-form-urlencoded` and includes:

    * parameters for OAuth and Openid connect:
        * `grant_type`: must be `authorization_code`
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

    if grant_type == "authorization_code":
        db_authorization_code = await cruds_auth.get_authorization_token_by_token(
            db=db, code=code
        )
        if db_authorization_code is None:
            # TODO: add logging
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "The provided authorization code is invalid",
                },
            )

        # We need to check client id and secret
        if authorization is not None:
            # client_id and client_secret are base64 encoded in the Basic authorization header
            # TODO: If this is useful, create a function to decode Basic or Bearer authorization header
            client_id, client_secret = (
                base64.b64decode(authorization.replace("Basic ", ""))
                .decode("utf-8")
                .split(":")
            )

        if client_id is None or client_id not in known_clients:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "Invalid client_id",
                },
            )

        # If there is a client secret, we don't use PKCE
        if client_secret is not None:
            if (
                client_id not in known_clients
                or known_clients[client_id]["secret"] != client_secret
            ):
                # TODO: add logging
                print("Invalid client id or secret")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "invalid_client",
                        "error_description": "Invalid client id or secret",
                    },
                )
        # If there is no client secret, we use PKCE
        elif (
            db_authorization_code.code_challenge is not None
            and code_verifier is not None
        ):
            # We need to verify the hash correspond
            if (
                db_authorization_code.code_challenge
                != hashlib.sha256(code_verifier.encode()).hexdigest()
                # We need to pass the code_verifier as a b-string, we use `code_verifier.encode()` for that
                # TODO: Make sure that `.hexdigest()` is applied by the client to code_challenge
            ):
                # TODO: add logging
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_request",
                        "error_description": "Invalid code_verifier",
                    },
                )
        else:
            # TODO: add logging
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "Client must provide a client_secret or a code_verifier",
                },
            )

        # We can check the authorization code
        if db_authorization_code.expire_on < datetime.now():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "Expired authorization code",
                },
            )
        await cruds_auth.delete_authorization_token_by_token(db=db, code=code)

        # TODO
        # We let the client hardcode a redirect url
        if known_clients[client_id]["redirect_uri"] != "":
            redirect_uri = known_clients[client_id]["redirect_uri"]

        # Ensure that the redirect_uri parameter value is identical to the redirect_uri parameter value that was included in the initial Authorization Request.
        # If the redirect_uri parameter value is not present when there is only one registered redirect_uri value, the Authorization Server MAY return an error (since the Client should have included the parameter) or MAY proceed without an error (since OAuth 2.0 permits the parameter to be omitted in this case).
        if redirect_uri is None:
            redirect_uri = db_authorization_code.redirect_uri
        if redirect_uri != db_authorization_code.redirect_uri:
            # TODO add logging
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "redirect_uri should remain identical",
                },
            )

        access_token_data = {
            "sub": db_authorization_code.user_id,
            # "scope": "scopes",
        }
        # Expiration date is included by `create_access_token` function
        access_token = create_access_token(data=access_token_data)

        # We will create an OAuth response, then add oidc specific elements if required
        response_body = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid",  # openid required by nextcloud
            # "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",  # What type, JWT ? No, we should be able to invalidate
            # "example_parameter": "example_value",  # ???
        }

        if (
            db_authorization_code.scope is not None
            and "openid" in db_authorization_code.scope
        ):
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

            id_token_data = {
                "iss": AUTH_ISSUER,
                "sub": db_authorization_code.user_id,
                "aud": client_id,
                # "exp"included by the function
                "iat": datetime.utcnow(),
            }
            if db_authorization_code.nonce is not None:
                # oidc only, required if provided by the client
                id_token_data["nonce"] = db_authorization_code.nonce

            id_token = create_access_token_RS256(id_token_data)

            response_body["id_token"] = id_token

        print("Response body", response_body)

        # Required headers by Oauth and oidc
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response_body

    elif grant_type == "refresh_token":
        # Why doesn't this step use PKCE: https://security.stackexchange.com/questions/199000/oauth2-pkce-can-the-refresh-token-be-trusted
        # TODO: implement
        print("Not implemented")
        raise HTTPException(
            status_code=401,
            detail="Not implemented",
        )
    else:
        print("invalid grant")
        raise HTTPException(
            status_code=401,
            detail="invalid_grant",
        )


@router.get("/auth/userinfo")
async def auth_get_userinfo(
    request: Request,
    user: models_core.CoreUser = Depends(get_current_user),
):  # productId: int = Body(...)):  # , request: Request):
    # access_token = authorization
    return {
        "sub": user.id,
        "name": user.firstname,
        "given_name": user.nickname,
        "family_name": user.name,
        "preferred_username": user.nickname,
        "email": user.email,
        "picture": "",
    }


@router.get("/oidc/authorization-flow/jwks_uri")
def jwks_uri():
    return {
        "keys": [
            {
                "kty": "RSA",
                "e": "AQAB",
                "use": "sig",
                "kid": "sig-16525550979",
                "alg": "RS256",
                "n": "kMhrv7o-00T2kw2jF_J1O9kLRQOlFudYvCmunQ5uPfqbQ0IIpMKwN7ZEj5PyRbBhoyWQ3yHC9NPwvsyqdzH9mMFyaBikdGVXBbeKmMjc9PU4zrR_i3mwY2_PrPY4IuV5TLEv8gq-maAXxrQr5vGeUcq2rbdJTwjY3jXRMGU2q-AHjtq13gDtrR-4yYPVumnjzAaZrntpDLx_SHBn7fyl8KxdGsZcO6xq5Y9Wa9ClVvSsYj724zvWeSUbqZ3VxV-mjzKbYSITeUilNrgeavpHKGRo_6tU3soPruOvAU-2gdDLLdXszIv-jU3LFAUw8p1Ey92OCwf98bjr4qRtuAb2XQ",
            }
        ]
    }


@router.get("/.well-known/openid-configuration")
async def oidc_configuration():

    return {
        "request_parameter_supported": True,
        "id_token_encryption_alg_values_supported": [
            "RSA-OAEP",
            "RSA1_5",
            "RSA-OAEP-256",
        ],
        "registration_endpoint": "https://a/register",
        "userinfo_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
        ],
        "token_endpoint": "http://host.docker.internal:8000/auth/token",
        "request_uri_parameter_supported": False,
        "request_object_encryption_enc_values_supported": [
            "A192CBC-HS384",
            "A192GCM",
            "A256CBC+HS512",
            "A128CBC+HS256",
            "A256CBC-HS512",
            "A128CBC-HS256",
            "A128GCM",
            "A256GCM",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "client_secret_jwt",
            "private_key_jwt",
            "none",
        ],
        "userinfo_encryption_alg_values_supported": [
            "RSA-OAEP",
            "RSA1_5",
            "RSA-OAEP-256",
        ],
        "subject_types_supported": ["public", "pairwise"],
        "id_token_encryption_enc_values_supported": [
            "A192CBC-HS384",
            "A192GCM",
            "A256CBC+HS512",
            "A128CBC+HS256",
            "A256CBC-HS512",
            "A128CBC-HS256",
            "A128GCM",
            "A256GCM",
        ],
        "claims_parameter_supported": False,
        "jwks_uri": "http://host.docker.internal:8000/oidc/authorization-flow/jwks_uri",
        "id_token_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "none",
        ],
        "authorization_endpoint": "http://127.0.0.1:8000/auth/authorize",
        "require_request_uri_registration": False,
        "introspection_endpoint": "https://c/introspect",
        "request_object_encryption_alg_values_supported": [
            "RSA-OAEP",
            "?RSA1_5",
            "RSA-OAEP-256",
        ],
        "service_documentation": "https://d/about",
        "response_types_supported": ["code", "token"],
        "token_endpoint_auth_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
        ],
        "revocation_endpoint": "https://e/revoke",
        "request_object_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
        ],
        "claim_types_supported": ["normal"],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_credentials",
            "urn:ietf:params:oauth:grant_type:redelegate",
        ],
        "scopes_supported": [
            "profile",
            "openid",
            "email",
            "address",
            "phone",
            "offline_access",
        ],
        "userinfo_endpoint": "http://host.docker.internal:8000/auth/userinfo",
        "userinfo_encryption_enc_values_supported": [
            "A192CBC-HS384",
            "A192GCM",
            "A256CBC+HS512",
            "A128CBC+HS256",
            "A256CBC-HS512",
            "A128CBC-HS256",
            "A128GCM",
            "A256GCM",
        ],
        "op_tos_uri": "https://g/about",
        "issuer": AUTH_ISSUER,
        "op_policy_uri": "https://idp-p.mitre.org/about",
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
    }

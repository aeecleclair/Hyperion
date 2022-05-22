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
from fastapi.responses import RedirectResponse
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
from app.dependencies import get_db
from app.models import models_core
from app.schemas import schemas_core
from app.utils.types.tags import Tags

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


# Authentication Request
# Common to OAuth 2.0 and OIDC

known_clients = {"application": "secret"}


# http://127.0.0.1:8000/auth/authorize?response_type=code&client_id=1234&redirect_uri=h&scope=&state=

# Add post
@router.get(
    "/auth/authorize",
)
async def authorize_page(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None = None,  # Optional for OAuth but must contain "openid" for oidc
    state: str | None = None,  # RECOMMENDED
    nonce: str | None = None,  # oidc only
    code_challenge: str | None = None,  # PKCE only
    code_challenge_method: str | None = None,  # PKCE only
    db: AsyncSession = Depends(get_db),
):
    """
    This endpoint is the one the user is redirected to when beginning the authorization process.
    The page should allow the user to login and choose if he want to authorize the client.

    The following query parameters are required for Oauth2 Authorization Code Grant flow.
    They need to be passed to the authorization endpoint `/auth/authorize`

    `response_type: str`: The flow that will be used
    `redirect_uri: str`: Url we need to redirect to after the authorization
    `client_id: str`: Client identifier, needs to be registered in the server known_clients
    `scope: str`: Must contain `openid` for OIDC exchanges

    `state: str`: RECOMMENDED Opaque value used to maintain state between the request and the callback.
    `nonce: str`: OPTIONAL. String value used to associate a Client session with an ID Token, and to mitigate replay attacks. The value is passed through unmodified from the Authentication Request to the ID Token.


    **This endpoint is an UI endpoint and is not part of the authorization exchanges**
    """

    # Oauth authorization code grant expect to return a *code*
    # We may implement other flow later
    if response_type != "code":
        raise HTTPException(
            status_code=422,
            detail="Invalid or not implemented response_type, use Authorization Code Grant flow",
        )

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
    request: Request,
    email: str = Form(
        ...
    ),  # We use Form as parameters must be `application/x-www-form-urlencoded`
    password: str = Form(...),
    response_type: str = Form(...),  # We only support authorization `code` flow
    client_id: str = Form(...),
    redirect_uri: str | None = Form(None),  # Optional for OAuth but required for oidc ?
    scope: str
    | None = Form(None),  # Optional for OAuth, must contain "openid" for oidc
    state: str | None = Form(None),  # RECOMMENDED
    nonce: str | None = Form(None),  # oidc only
    code_challenge: str | None = Form(None),  # PKCE only
    code_challenge_method: str | None = Form(None),  # PKCE only
    db: AsyncSession = Depends(get_db),
):
    """
    Part 1 of the authorization code grant.

    Parameters must be `application/x-www-form-urlencoded` and includes:

    * parameters for the client which want to get an authorization:
    `response_type: str`: The flow that will be used
    `redirect_uri: str`: Url we need to redirect to after the authorization
    `client_id: str`: Client identifier, needs to be registered in the server known_clients
    `scope: str`: Must contain `openid` for OIDC exchanges

    `state: str`: RECOMMENDED Opaque value used to maintain state between the request and the callback.
    `nonce: str`: OPTIONAL. String value used to associate a Client session with an ID Token, and to mitigate replay attacks. The value is passed through unmodified from the Authentication Request to the ID Token.


    * parameters that allows to authenticate the user and know which scopes it want to grant access to.
    `email: str`
    `password: str`

    Note: we may want to require a JWT here, instead of email/password!
    Note: we should add a way to indicate which ressources the client should be granted access

    References:
     - https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2
    """
    # TODO: implement nonce and scope

    # TODO: error handling https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2.1

    # Request example from Nextcloud social login app
    # ?response_type=code&client_id=myeclnextcloud&redirect_uri=http://localhost:8009/apps/sociallogin/custom_oauth2/myecl&scope=&state=HA-HJIDEGL6MQTCW2B3Z8914OUN5X0SPVYR7KAF

    # We need to authenticate the user here:
    # TODO: we should not use the password like this. Should we use a bearer ?
    # TODO: clarify this part
    user = await authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Oauth authorization code grant expect to return a *code*
    # We may implement other flow later
    if response_type != "code":
        raise HTTPException(
            status_code=422,
            detail="Invalid or not implemented response_type, use Authorization Code Grant flow",
        )

    # We want to check `client_id`. Generally clients have to be registered in the authorization server
    if client_id not in known_clients:
        raise HTTPException(
            status_code=422,
            detail="Invalid client_id",
        )

    # We generate a new authorization_code
    # The authorization code MUST expire
    # shortly after it is issued to mitigate the risk of leaks.  A
    # maximum authorization code lifetime of 10 minutes is
    # RECOMMENDED.  The client MUST NOT use the authorization code more than once.
    authorization_code = generate_token()
    expire_on = datetime.now() + timedelta(hours=1)

    # We save this authorization_code to the database
    # TODO: could we use a JWT?
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

    # TODO
    # Lack of a redirection URI registration requirement can enable an
    # attacker to use the authorization endpoint as an open redirector as
    # described in Section 10.15.

    # TODO: scope must contain openid for oidc

    # TODO make optionnal
    if redirect_uri is None:
        raise HTTPException(
            status_code=422,
            detail="Redirect URI should be passed for the moment",
        )

    # We need to redirect to the `redirect_uri` provided by the *client* providing the new authorization_code.
    # For security reason, we need to provide the same `state` that was send by the client in the first request
    url = (
        redirect_uri.replace("%3A", ":").replace("%2F", "/")
        + "?code="
        + authorization_code
    )
    if state:
        url += "&state=" + state
    if nonce:
        url += "&nonce=" + nonce
    return RedirectResponse(url)


@router.post("/auth/token")
async def token(
    # res: schemas_core.TokenReq,
    request: Request,
    response: Response,
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str | None = Form(None),
    authorization: str | None = Header(default=None),
    client_id: str = Form(...),
    client_secret: str | None = Form(None),
    code_verifier: str | None = Form(None),  # For PKCE
    db: AsyncSession = Depends(get_db),
):  # productId: int = Body(...)):  # , request: Request):
    """
    Part 3 of the authorization code grant.
    The client ask to exchange its authorization code for an access token

    https://openid.net/specs/openid-connect-core-1_0.html#TokenRequestValidation
    """

    # TODO: error handling

    db_authorization_code = await cruds_auth.get_authorization_token_by_token(
        db=db, code=code
    )
    if db_authorization_code is None:
        raise HTTPException(
            status_code=422,
            detail="Invalid authorization code",
        )

    # We need to check client id and secret
    if authorization is not None:
        # client_id and client_secret are base64 encoded in the authorization header
        # TODO: use a function
        # TODO is "Bearer" missing
        client_id, client_secret = (
            base64.b64decode(authorization).decode("utf-8").split(":")
        )

    if client_id is not None and client_secret is not None:
        if client_id not in known_clients and known_clients[client_id] != client_secret:
            raise HTTPException(
                status_code=403,
                detail="Invalid client_id or client_secret",
            )
    elif db_authorization_code.code_challenge is not None and code_verifier is not None:
        # We need to verify the hash correspond
        if (
            db_authorization_code.code_challenge
            != hashlib.sha256(code_verifier.encode()).hexdigest()
            # We need to pass the code_verifier as a b-string, we use `code_verifier.encode()` for that
            # TODO: Make sure that `.hexdigest()` is applied by the client to code_challenge
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid code_verifier",
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Client must provide a client_id and client_secret",
        )

    # We can check the authorization code
    if db_authorization_code.expire_on > datetime.now():
        raise HTTPException(
            status_code=422,
            detail="Expired authorization code",
        )
    await cruds_auth.delete_authorization_token_by_token(db=db, code=code)

    # Ensure that the redirect_uri parameter value is identical to the redirect_uri parameter value that was included in the initial Authorization Request. If the redirect_uri parameter value is not present when there is only one registered redirect_uri value, the Authorization Server MAY return an error (since the Client should have included the parameter) or MAY proceed without an error (since OAuth 2.0 permits the parameter to be omitted in this case).
    if redirect_uri != db_authorization_code.redirect_uri:
        raise HTTPException(
            status_code=422,
            detail="redirect_uri should remain identical",
        )

    access_token_data = {
        "sub": db_authorization_code.user_id
    }  # + exp included by the function
    access_token = create_access_token(data=access_token_data)

    # We will create an OAuth response, then add oidc specific elements if required
    response_body = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",  # What type, JWT ? No, we should be able to invalidate
        "example_parameter": "example_value",  # ???
    }

    if (
        db_authorization_code.scope is not None
        and "openid" in db_authorization_code.scope
    ):
        # It's an openid connect request, we need to return an `id_token`

        # Required :
        # aud existence
        # iss existence and value : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
        # https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016

        id_token_data = {
            "iss": "http://127.0.0.1:8000/",
            "sub": db_authorization_code.user_id,
            "aud": client_id,
            # "exp": 0,      # Included by the function
            # "auth_time": "" # not sure
            "iat": 0,  # Required for oidc
            "nonce": db_authorization_code.nonce,  # oidc only, required if provided by the client
        }

        id_token = create_access_token_RS256(id_token_data)

        response_body["id_token"] = (id_token,)

    print("Response body", response_body)

    # Required headers by Oauth and oidc
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response_body


@router.get("/auth/userinfo", de)
async def auth_get_userinfo(
    request: Request,
    authorization: str = Header(default=None),
):  # productId: int = Body(...)):  # , request: Request):
    access_token = authorization
    return {
        "sub": "248289761001",
        "name": "Jane Doe",
        "given_name": "Jane",
        "family_name": "Doe",
        "preferred_username": "j.doe",
        "email": "janedoe@example.com",
        "picture": "http://example.com/janedoe/me.jpg",
    }


"""
from jose import jwt

claims = {"hello": "world"}
key = {
    "kty": "RSA",
    "d": "RSjC9hfDtq2G3hQJFBI08hu3CJ6hRRlhs-u9nMFhdSpqhWFPK3LuLVSWPxG9lN7NQ963_7AturR9YoEvjXjCMZFEEqewNQNq31v0zgh9k5XFdz1CiVSLdHo7VQjuJB6imLCF266TUFvZwQ4Gs1uq6I6GCVRoenSe9ZsWleYF--E",
    "e": "AQAB",
    "use": "sig",
    "kid": "1234567890",
    "alg": "RS256",
    "n": "thBvC_I9NciW6XqTxUFMZaVVpvGx6BvLHd3v8Visk_6OoDCVXF_6vNktNi6W7CBkuHBqGyuF0wDFrHcZuZq_kLKI6IRofEzKyUoReOyYRlPt5ar64oDO-4mwH47fb99ILW94_8RpQHy74hCnfv7d888YaCmta9iOBOvggcvxb5s",
}

token = jwt.encode(
    {"sub": "12345678"},
    key,
    algorithm="RS256",
)


pubandpriv = {
    "p": "4kom51UNpLnMUjSzhu5yYI1kHub2Pp-a_13h2Zd_RFYM3Uyo_KSHRFABK_lf1P_yF7eGmkQqi1MLFrVD8A7bdBAbFZmJg1jOpJL-qjGA3YBhP8OCj_AKqpbaY3VVpWmnS9E0qTARaJuDgN18nQSBf9lJOlSsb9GjHgcRiUhrhd0",
    "kty": "RSA",
    "q": "o8q8UucMLu0Khg9hX08ei4sFNzSLnjxM7QTXMiDWr9G1WSl7r-wwkTJmuFWp_HacrdWQ6fz4ofVcKlGWs_Eaotij8E6C1QNySdyr7Utx5k_T9dwsiAdoZwrr88Ads0XIvDenJgqX9UWhpDoGCpRASWqfT8BQ6m4DdFt3z_LnaoE",
    "d": "kKFl4bVvpSUzHFt3HSj7q7l55Itrk6GvpugMoqATyJ5cE6gXcl96IW1WuAcW8j7sikmwmvXjByfhSvixITkzGDHG0-4p-oxxjih3r4CYGawN_4-YCgCaD_tV_nZIRbPupIosVyIcnOKsXbcGVEHx4csbChYaiXVRD0m7mxjAsJgpx2lOe8Gc4cJTZ3gWjSVA7JChPGVFglIYHJo65u2KlCY0TCmojqKdyNtSxyRn67ZgDXbGsN7pxOMjUYykX4zAD4tPOhJXRPy7vcTpkUa4EpO0QqJ7RK5GQ1uYpPGSV-KJjpq8h0tZLiG9Dq5n_veeQ4ajWlnuhKiH980Vfi1oAQ",
    "e": "AQAB",
    "use": "sig",
    "kid": "sig-1652555097",
    "qi": "myiQFKf_pFmgmCJ6xFQO7quBSbU6yI_2-n7nVcGenyq7vx89Pp5MNVgl_l-OtiNTucuku8BEf_kAbf8OWz0ANNIT2A0du6HYT8arK_-RwLvHiXu72XVTBQZBpqaprrn5bXnbT7u-1Fs0c-ykHdXJIxalArP7A1v94Cl5BeBM298",
    "dp": "WCsqM1JJaZhXCuSr2nQHrqUIkJ3O7iGD4-HxgLVtifO5OXSIF0AH0E8X1clpVHWRHzqLwIm0xepKVMO1v9AaI4Ou-eCD2uB8S1VW0ntNSYCe45hKw8h0b3ktiDkMcNHUtE7EJPOspMSLHWevCQLbbjP8OzUIptzYoHeClqnX8yU",
    "alg": "RS256",
    "dq": "KJ9Zgb4n-WN03rbl0XuP-c_q5Tw0_HO8KHSw4o_ebxC1x31QXdtYWEqFy2YDmMfaKAr1u_Kvv4tY5m4B0HMVxhmw3yK5tBb8u3DtexbhEtvtl-aZbMtZi2TcDEIzm4jNNlEfNYIfGgfBBTgW03zdTNgS1va9msbaOHuPBZYa6wE",
    "n": "kMhrv7o-00T2kw2jF_J1O9kLRQOlFudYvCmunQ5uPfqbQ0IIpMKwN7ZEj5PyRbBhoyWQ3yHC9NPwvsyqdzH9mMFyaBikdGVXBbeKmMjc9PU4zrR_i3mwY2_PrPY4IuV5TLEv8gq-maAXxrQr5vGeUcq2rbdJTwjY3jXRMGU2q-AHjtq13gDtrR-4yYPVumnjzAaZrntpDLx_SHBn7fyl8KxdGsZcO6xq5Y9Wa9ClVvSsYj724zvWeSUbqZ3VxV-mjzKbYSITeUilNrgeavpHKGRo_6tU3soPruOvAU-2gdDLLdXszIv-jU3LFAUw8p1Ey92OCwf98bjr4qRtuAb2XQ",
}

pub = {
    "kty": "RSA",
    "e": "AQAB",
    "use": "sig",
    "kid": "sig-1652555097",
    "alg": "RS256",
    "n": "kMhrv7o-00T2kw2jF_J1O9kLRQOlFudYvCmunQ5uPfqbQ0IIpMKwN7ZEj5PyRbBhoyWQ3yHC9NPwvsyqdzH9mMFyaBikdGVXBbeKmMjc9PU4zrR_i3mwY2_PrPY4IuV5TLEv8gq-maAXxrQr5vGeUcq2rbdJTwjY3jXRMGU2q-AHjtq13gDtrR-4yYPVumnjzAaZrntpDLx_SHBn7fyl8KxdGsZcO6xq5Y9Wa9ClVvSsYj724zvWeSUbqZ3VxV-mjzKbYSITeUilNrgeavpHKGRo_6tU3soPruOvAU-2gdDLLdXszIv-jU3LFAUw8p1Ey92OCwf98bjr4qRtuAb2XQ",
}

token = jwt.encode(
    {"hello": "world"},
    pubandpriv,
    algorithm="RS256",
)


jwt.decode(token, pub)
"""


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
        "token_endpoint": "http://host.docker.internal:8000/oidc/authorization-flow/token",
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
        "authorization_endpoint": "http://127.0.0.1:8000/auth/authorization-flow/authorize-page",
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
        "userinfo_endpoint": "http://host.docker.internal:8000/oidc/authorization-flow/userinfo",
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
        "issuer": "hyperion",
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

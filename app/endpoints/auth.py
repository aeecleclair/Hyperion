from fastapi import APIRouter, Depends, status, HTTPException, Request, Body, Form
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
from jose import jwt


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
    print("Hello")

    print("World")
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


# http://127.0.0.1:8000/auth/authorize-page?response_type=code&client_id=1234&redirect_uri=h&scope=&state=
@router.get(
    "/oidc/authorization-flow/authorize-page",
)
async def oidc_authorize_page(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    nonce: str,
    request: Request,
):
    """
    This endpoint is the one the user is redirected to when beginning the authorization process.
    The page should allow the user to login and choose if he want to authorize the client

    #The following query parameters are required for Oauth2 Authorization Code Grant flow.
    They need to be passed to the authorization endpoint `/auth/authorize`
    ```python
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    ```
    # Plus     nonce: str


    **This endpoint is an UI endpoint and is not part of the authorization exchanges**
    """
    return templates.TemplateResponse(
        "oidc-connexion.html",
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
    "/oidc/authorization-flow/authorize",
)
async def authorizer(
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


@router.post("/oidc/authorization-flow/token")
async def oidc_authorization_flow_token(
    # res: schemas_core.TokenReq,
    request: Request,
    grant_type: str = Form(...),
    # client_id: str = Form(...),
    # client_secret: str = Form(...),
    redirect_uri=Form(...),
    code: str = Form(...),
):  # productId: int = Body(...)):  # , request: Request):
    """
    Part 3 of the authorization code grant.
    The client ask to exchange its authorization code for an access token
    """
    # TODO: NOT IMPLEMENTED!

    print("OIDC token")

    pubandpriv = {
        "p": "4kom51UNpLnMUjSzhu5yYI1kHub2Pp-a_13h2Zd_RFYM3Uyo_KSHRFABK_lf1P_yF7eGmkQqi1MLFrVD8A7bdBAbFZmJg1jOpJL-qjGA3YBhP8OCj_AKqpbaY3VVpWmnS9E0qTARaJuDgN18nQSBf9lJOlSsb9GjHgcRiUhrhd0",
        "kty": "RSA",
        "q": "o8q8UucMLu0Khg9hX08ei4sFNzSLnjxM7QTXMiDWr9G1WSl7r-wwkTJmuFWp_HacrdWQ6fz4ofVcKlGWs_Eaotij8E6C1QNySdyr7Utx5k_T9dwsiAdoZwrr88Ads0XIvDenJgqX9UWhpDoGCpRASWqfT8BQ6m4DdFt3z_LnaoE",
        "d": "kKFl4bVvpSUzHFt3HSj7q7l55Itrk6GvpugMoqATyJ5cE6gXcl96IW1WuAcW8j7sikmwmvXjByfhSvixITkzGDHG0-4p-oxxjih3r4CYGawN_4-YCgCaD_tV_nZIRbPupIosVyIcnOKsXbcGVEHx4csbChYaiXVRD0m7mxjAsJgpx2lOe8Gc4cJTZ3gWjSVA7JChPGVFglIYHJo65u2KlCY0TCmojqKdyNtSxyRn67ZgDXbGsN7pxOMjUYykX4zAD4tPOhJXRPy7vcTpkUa4EpO0QqJ7RK5GQ1uYpPGSV-KJjpq8h0tZLiG9Dq5n_veeQ4ajWlnuhKiH980Vfi1oAQ",
        "e": "AQAB",
        "use": "sig",
        "kid": "sig-16525550979",  # "sig-1652555097",
        "qi": "myiQFKf_pFmgmCJ6xFQO7quBSbU6yI_2-n7nVcGenyq7vx89Pp5MNVgl_l-OtiNTucuku8BEf_kAbf8OWz0ANNIT2A0du6HYT8arK_-RwLvHiXu72XVTBQZBpqaprrn5bXnbT7u-1Fs0c-ykHdXJIxalArP7A1v94Cl5BeBM298",
        "dp": "WCsqM1JJaZhXCuSr2nQHrqUIkJ3O7iGD4-HxgLVtifO5OXSIF0AH0E8X1clpVHWRHzqLwIm0xepKVMO1v9AaI4Ou-eCD2uB8S1VW0ntNSYCe45hKw8h0b3ktiDkMcNHUtE7EJPOspMSLHWevCQLbbjP8OzUIptzYoHeClqnX8yU",
        "alg": "RS256",
        "dq": "KJ9Zgb4n-WN03rbl0XuP-c_q5Tw0_HO8KHSw4o_ebxC1x31QXdtYWEqFy2YDmMfaKAr1u_Kvv4tY5m4B0HMVxhmw3yK5tBb8u3DtexbhEtvtl-aZbMtZi2TcDEIzm4jNNlEfNYIfGgfBBTgW03zdTNgS1va9msbaOHuPBZYa6wE",
        "n": "kMhrv7o-00T2kw2jF_J1O9kLRQOlFudYvCmunQ5uPfqbQ0IIpMKwN7ZEj5PyRbBhoyWQ3yHC9NPwvsyqdzH9mMFyaBikdGVXBbeKmMjc9PU4zrR_i3mwY2_PrPY4IuV5TLEv8gq-maAXxrQr5vGeUcq2rbdJTwjY3jXRMGU2q-AHjtq13gDtrR-4yYPVumnjzAaZrntpDLx_SHBn7fyl8KxdGsZcO6xq5Y9Wa9ClVvSsYj724zvWeSUbqZ3VxV-mjzKbYSITeUilNrgeavpHKGRo_6tU3soPruOvAU-2gdDLLdXszIv-jU3LFAUw8p1Ey92OCwf98bjr4qRtuAb2XQ",
    }

    # Required :
    # aud existence
    # iss existence and value : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
    # https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016
    token = jwt.encode(
        {"sub": "12345678", "aud": "application", "iss": "hyperion"},
        pubandpriv,
        algorithm="RS256",
    )

    print("___   ", token)

    # print(await request.json())
    # print(request)
    return {
        "token_type": "Bearer",
        "expires_in": 86400,
        "access_token": token,  # "54td0ipRa4inEk9DJwB-asR6nFAlRHLJwOx-r0XmVfXkeIScr3FEFO6gZwvul9x4U0ZaLnsV",
        "scope": "openid profile email photo",
        "id_token": token,
    }


@router.get("/oidc/authorization-flow/userinfo")
async def oidc_authorization_flow_userinfo(
    request: Request,
):  # productId: int = Body(...)):  # , request: Request):
    return {
        "sub": "83692",
        "name": "Alice Adams",
        "given_name": "Alice",
        "family_name": "Adams",
        "email": "alice@example.com",
        "picture": "https://example.com/83692/photo.jpg",
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
    """
    Part 3 of the authorization code grant.
    The client ask to exchange its authorization code for an access token
    """

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

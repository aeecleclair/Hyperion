from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.core.security import create_access_token

from app.dependencies import get_db
from app.schemas import schemas_core
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import authenticate_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.types.tags import Tags
from app.core.security import generate_token
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/sso", status_code=200, tags=[Tags.auth], response_class=HTMLResponse)
async def sso(db: AsyncSession = Depends(get_db)):
    return """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """


# Authorization Code Grant

# https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/
# https://www.oauth.com/oauth2-servers/server-side-apps/example-flow/


@router.get(
    "/auth/authorize",
)
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    if response_type == "code":
        print(client_id)
        # http://127.0.0.1:8000/auth/authorize?response_type=code&client_id=myeclnextcloud&redirect_uri=http://localhost:8009/apps/sociallogin/custom_oauth2/myecl&scope=&state=HA-HJIDEGL6MQTCW2B3Z8914OUN5X0SPVYR7KAF
        authorization_code = generate_token()
        # return "Success: " + authorization_code
        url = (
            redirect_uri.replace("%3A", ":").replace("%2F", "/")
            + "?code="
            + authorization_code
            + "&state="
            + state
        )
        return RedirectResponse(url)
    raise HTTPException(status_code=422, detail="Invalid response_type")


@router.post(
    "/auth/authorizetoken",
)
async def authorizetoken(request: Request):
    print(request)
    return {
        "access_token": "AYjcyMzY3ZDhiNmJkNTY",
        "refresh_token": "RjY2NjM5NzA2OWJjuE7c",
        "token_type": "Bearer",
        "expires": 3600,
    }


@router.get(
    "/auth/profil",
)
async def profil(request: Request):
    # Fields are :
    # https://github.com/zorn-v/nextcloud-social-login/blob/e0e6deef8288daf04f557c0f124c63b6e975f0c0/lib/Provider/CustomOAuth2.php
    return {
        "identifier": "12345678910",
        "name": "Jhobahtes",
        "username": "Jhobahtes",
        "family_name": "Parecki",
        "picture": "https://lh4.googleusercontent.com/-kw-iMgDj34/AAAAAAAAAAI/AAAAAAAAAAc/P1YY91tzesU/photo.jpg",
        "email": "aaron.parecki@okta.com",
        "email_verified": True,
        "locale": "en",
        "hd": "okta.com",
    }


"""
    grant_type: str,
    code: str,
    redirect_uri: str,
    scope: str,
    db: AsyncSession = Depends(get_db),
):
    print(grant_type)
    print("-------")
"""

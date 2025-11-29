"""Schemas file for endpoint /auth"""

from datetime import datetime
from typing import Literal

from fastapi import Form
from pydantic import BaseModel, field_validator

from app.utils import validators
from app.utils.examples import examples_auth


class Authorize(BaseModel):
    client_id: str
    redirect_uri: str | None = None
    response_type: str
    scope: str | None = None
    state: str | None = None
    nonce: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None


class AuthorizeValidation(Authorize):
    """
    Oauth specifications specifies that all parameters should be `application/x-www-form-urlencoded`.
    This schema is configured to requires Form(...) parameters.

    The endpoint needs to depend on this class:
    ```python
        authorizereq: schemas_auth.AuthorizeValidation = Depends(
            schemas_auth.AuthorizeValidation.as_form
        ),
    ```
    """

    email: str
    password: str

    # If we don't add these parameters
    # the heritage from Authorize does not allow Mypy to infer the str | None
    redirect_uri: str | None = None
    scope: str | None = None
    state: str | None = None
    nonce: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None

    # Email normalization, this will modify the email variable
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_email = field_validator(
        "email",
    )(validators.email_normalizer)

    class config:
        schema_extra = {"example": examples_auth.example_AuthorizeValidation}

    @classmethod
    def as_form(
        cls,
        client_id: str = Form(...),
        redirect_uri: str | None = Form(None),
        response_type: str = Form(...),
        scope: str | None = Form(None),
        state: str | None = Form(None),
        nonce: str | None = Form(None),
        code_challenge: str | None = Form(None),
        code_challenge_method: str | None = Form(None),
        email: str = Form(...),
        password: str = Form(...),
    ):
        if nonce == "None":
            nonce = None

        return cls(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            email=email,
            password=password,
        )


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str  # Subject: the user id
    iss: str | None = None
    aud: str | None = None
    cid: str | None = None  # The client_id of the service which receives the token
    iat: datetime | None = None
    nonce: str | None = None
    scopes: str = ""
    # exp and iat elements are added by the token generation function


class TokenReq(BaseModel):
    refresh_token: str | None = None
    grant_type: str
    code: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    # PKCE parameters
    code_verifier: str | None = None

    @classmethod
    def as_form(
        cls,
        refresh_token: str | None = Form(None),
        grant_type: str = Form(...),
        code: str | None = Form(None),
        redirect_uri: str | None = Form(None),
        client_id: str | None = Form(None),
        client_secret: str | None = Form(None),
        # PKCE parameters
        code_verifier: str | None = Form(None),
    ):
        return cls(
            refresh_token=refresh_token,
            grant_type=grant_type,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
            code_verifier=code_verifier,
        )

    class config:
        schema_extra = {
            "example": {
                "refresh_token": "Yi6wBcMVoUe-dYJ-ttd6dT8ZuKcUsJVnc4MaUxoLeXU",
                "grant_type": "refresh_token",
                "client_id": "5507cc3a-fd29-11ec-b939-0242ac120002",
            },
        }


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int = 1800
    scope: str = ""
    refresh_token: str
    id_token: str | None = None


class IntrospectTokenReq(BaseModel):
    # https://datatracker.ietf.org/doc/html/rfc7662
    token: str
    token_type_hint: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    @classmethod
    def as_form(
        cls,
        token: str = Form(...),
        token_type_hint: str | None = Form(None),
        client_id: str | None = Form(None),
        client_secret: str | None = Form(None),
    ):
        return cls(
            token=token,
            token_type_hint=token_type_hint,
            client_id=client_id,
            client_secret=client_secret,
        )


class IntrospectTokenResponse(BaseModel):
    active: bool

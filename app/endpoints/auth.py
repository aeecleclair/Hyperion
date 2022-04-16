from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import create_access_token

from app.dependencies import get_db
from app.schemas import schemas_core
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import authenticate_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.types.tags import Tags


router = APIRouter()


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
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

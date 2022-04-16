"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal

from fastapi import Depends, HTTPException, status
from jose import jwt
from pydantic import ValidationError

from app.core import security
from app.core.settings import settings
from app.cruds import cruds_users
from app.models import models_core
from app.schemas import schemas_core


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session
    """

    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(security.oauth2_scheme)
) -> models_core.CoreUser:
    """
    Make sure the token is valid and return the corresponding user.
    """
    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[security.jwt_algorithme],
        )
        token_data = schemas_core.TokenData(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user_id = token_data.sub

    user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

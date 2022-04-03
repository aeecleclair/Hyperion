from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas import schemas_tokens
from app.core import security
from app.core.settings import settings
from app.cruds import cruds_users
from app.models import models_users

from app.database import SessionLocal

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models_users.CoreUser:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas_tokens.TokenData(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = cruds_users.get_user_token_by_username(db, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

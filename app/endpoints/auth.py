from datetime import timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import create_access_token
from app.core.settings import settings

from app.database import SessionLocal
from app.dependencies import get_db
from app import cruds, schemas
from sqlalchemy.orm import Session
from app.schemas import schemas_tokens
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.core.security import authenticate_user

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@router.post("/auth/token", response_model=schemas_tokens.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

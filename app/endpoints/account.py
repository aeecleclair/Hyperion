from http.client import HTTPException
from fastapi import APIRouter, Depends

from app.database import SessionLocal, engine
from app.dependencies import get_db
from app.cruds import cruds_users
from app.schemas import schemas_users

from sqlalchemy.orm import Session

from app.models import models_users

models_users.Base.metadata.create_all(bind=engine)
router = APIRouter()


@router.post("/account/create", response_model=schemas_users.CoreUser)
def create_account(user: schemas_users.CoreUserCreate, db: Session = Depends(get_db)):
    # db_user = crud.get_user_by_email(db, email=user.email)
    # if db_user:
    #     raise HTTPException(status_code=400, detail="Email already registered")
    return cruds_users.create_user(db=db, user=user)

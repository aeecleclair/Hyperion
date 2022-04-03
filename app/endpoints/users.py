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


@router.post("/users/", response_model=schemas_users.CoreUser)
def create_user(user: schemas_users.CoreUserCreate, db: Session = Depends(get_db)):
    # db_user = crud.get_user_by_email(db, email=user.email)
    # if db_user:
    #     raise HTTPException(status_code=400, detail="Email already registered")
    return cruds_users.create_user(db=db, user=user)


@router.get("/users/", response_model=list[schemas_users.CoreUser])
def read_users(db: SessionLocal = Depends(get_db)):
    users = cruds_users.get_users(db)
    return users


@router.get("/users/{user_id}", response_model=schemas_users.CoreUser)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = cruds_users.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/users/{user_id}")
async def edit_user(user_id):

    return ""


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    cruds_users.delete_user(db, user_id=user_id)
    return f"Utilisateur {user_id} supprimé !"

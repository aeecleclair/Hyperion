from http.client import HTTPException
from fastapi import APIRouter, Depends

from app.database import SessionLocal
from app.dependencies import get_db
from app import crud, schemas
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/users/", response_model=schemas_users.CoreUser)
def create_user(user: schemas_users.CoreUserCreate, db: Session = Depends(get_db)):
    return cruds_users.create_user(db=db, user=user)

@router.post("/users/", response_model=schemas.CoreUser)
def create_user(user: schemas.CoreUserCreate, db: Session = Depends(get_db)):
    # db_user = crud.get_user_by_email(db, email=user.email)
    # if db_user:
    #     raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@router.get("/users/", response_model=list[schemas.CoreUser])
def read_users(db: SessionLocal = Depends(get_db)):
    users = crud.get_users(db)
    return users


@router.get("/users/{user_id}", response_model=schemas.CoreUser)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, user_id=user_id)
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

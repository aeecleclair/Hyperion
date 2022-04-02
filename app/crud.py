from sqlalchemy.orm import Session

from . import models, schemas


def get_users(db: Session):
    return db.query(models.Core_user).all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.Core_user).filter(models.Core_user.id == user_id).first()


def get_group(db: Session):
    return db.query(models.Core_group).all()


# def get_user_by_email(db: Session, email: str):
#     return db.query(models.User).filter(models.User.email == email).first()


# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.User).offset(skip).limit(limit).all()


# def create_user(db: Session, user: schemas.UserCreate):
#     fakePassword = user.password + "notreallyhashed"
#     db_user = models.User(email=user.email, hashed_password=fakePassword)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user


# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()


# def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
#     db_item = models.Item(**item.dict(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item

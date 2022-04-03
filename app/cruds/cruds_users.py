from sqlalchemy.orm import Session

from ..models import models_users
from ..schemas import schemas_users

from app.core import security


def get_users(db: Session):
    return db.query(models_users.CoreUser).all()


def get_user_token_by_login(db: Session, login: str):
    return (
        db.query(models_users.CoreUser)
        .filter(models_users.CoreUser.login == login)
        .first()
    )


def get_user_token_by_username(db: Session, username: str):
    return (
        db.query(models_users.CoreUser)
        .filter(models_users.CoreUser.firstname == username)
        .first()
    )


def get_user_by_id(db: Session, user_id: int):
    return (
        db.query(models_users.CoreUser)
        .filter(models_users.CoreUser.id == user_id)
        .first()
    )


def get_group(db: Session):
    return db.query(models_users.CoreGroup).all()


def delete_user(db: Session, user_id: int):
    db.query(models_users.CoreUser).filter(models_users.CoreUser.id == user_id).delete()
    db.commit()


def create_user(db: Session, user: schemas_users.CoreUserCreate):
    passwordhash = security.get_password_hash(user.password)
    db_user = models_users.CoreUser(
        login=user.login,
        password=passwordhash,
        name=user.name,
        firstname=user.firstname,
        nick=user.nick,
        birth=user.birth,
        promo=user.promo,
        floor=user.floor,
        created_on=user.created_on,
        email=user.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# def get_user_by_email(db: Session, email: str):
#     return db.query(models_users.User).filter(models_users.User.email == email).first()


# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models_users.User).offset(skip).limit(limit).all()


# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models_users.Item).offset(skip).limit(limit).all()


# def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
#     db_item = models_users.Item(**item.dict(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item

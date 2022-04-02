from sqlalchemy import Table, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

# from sqlalchemy.dialects.postgresql import UUID
# import uuid

from .database import Base


Core_membership = Table(
    "core_membership",
    Base.metadata,
    Column("user_id", ForeignKey("core_user.id"), primary_key=True),
    Column("group_id", ForeignKey("core_group.id"), primary_key=True),
)


class Core_user(Base):
    __tablename__ = "core_user"

    id = Column(Integer, primary_key=True, index=True)  # Use UID later
    login = Column(String)
    password = Column(String)  # the password is hashed
    name = Column(String)
    firstname = Column(String)
    nick = Column(String)
    birth = Column(String)
    promo = Column(String)
    floor = Column(String, default=None)
    email = Column(String, unique=True, index=True)
    created_on = Column(String)

    groups = relationship(
        "core_group", secondary=Core_membership, back_populates="members"
    )


class Core_group(Base):
    __tablename__ = "core_group"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    description = Column(String)

    members = relationship(
        "core_user", secondary=Core_membership, back_populates="groups"
    )


# class Core_associations(Base):
#     __tablename__ = "core_associations"

#     id =
#     type =

# class Core_groups(Base):
#     __tablename__ = "core_asso_admin"

#     id =
#     user_id =
#     asso_id =

#     id_gene = relationship("core_users", back_populates="id_asso_admin")


# class Item(Base):
#     __tablename__ = "items"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String, index=True)
#     description = Column(String, index=True)
#     owner_id = Column(Integer, ForeignKey("users.id"))

#     owner = relationship("User", back_populates="items")

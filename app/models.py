from click import password_option
from platformdirs import user_log_dir
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .database import Base


class Core_users(Base):
    __tablename__ = "core_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id_admin = relationship("Core_administrators", back_populates="id_gene")
    id_member = relationship("Core_membership", back_populates="id_gene")
    id_asso_admin = relationship("Core_asso_admin", back_populates="id_gene")


class Core_administrators(Base):
    __tablename__ = "core_administrators"
   
    user_id =
    id_gene = relationship("core_users", back_populates="id_admin")

class Core_membership(Base):
    __tablename__ = "core_membership"
   
    id =
    user_id = 
    asso_id =
    
    id_gene = relationship("core_users", back_populates="id_member")


class Core_associations(Base):
    __tablename__ = "core_associations"
    
    id =
    type =

class Core_asso_admin(Base):
    __tablename__ = "core_asso_admin"
    
    id =
    user_id =
    asso_id =

    id_gene = relationship("core_users", back_populates="id_asso_admin")


# class Item(Base):
#     __tablename__ = "items"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String, index=True)
#     description = Column(String, index=True)
#     owner_id = Column(Integer, ForeignKey("users.id"))

#     owner = relationship("User", back_populates="items")

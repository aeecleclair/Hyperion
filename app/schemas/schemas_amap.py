"""Schemas file for endpoint /amap"""

from datetime import date, datetime

from pydantic import BaseModel, validator

from app.utils.types.groups_type import AmapSlotType


class ProductBase(BaseModel):
    """Base schema for AMAP products"""

    id: str
    name: str
    price: float
    category: str


class ProductSimple(ProductBase):
    name: str
    price: float

    class Config:
        orm_mode = True


class ProductCreate(ProductBase):
    name: str
    price: float
    category: str

    class Config:
        orm_mode = True


class ProductEdit(ProductBase):
    name: str
    price: float

    class Config:
        orm_mode = True


class DeliveryBase(BaseModel):
    """Base schema for AMAP deliveries"""

    id: str
    deliveryDate: date
    products: list[ProductBase] = []


class DeliveryCreate(BaseModel):
    deliveryDate: date
    products: list[ProductBase] = []

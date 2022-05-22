"""Schemas file for endpoint /amap"""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
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


class OrderBase(BaseModel):
    """Base schema for AMAP orders"""

    order_id: str
    user: CoreUserSimple
    delivery_id: str
    products: list[ProductBase]
    amount: float
    collection_slot: AmapSlotType
    ordering_date: datetime
    delivery_date: date


class OrderCreate(OrderBase):
    user: CoreUserSimple
    delivery_id: str
    products: list[ProductBase]
    collection_slot: AmapSlotType
    delivery_date: date

    class Config:
        orm_mode = True


class OrderEdit(OrderBase):
    order_id: str
    user: CoreUserSimple
    delivery_id: str
    products: list[ProductBase]
    collection_slot: AmapSlotType
    delivery_date: date

    class Config:
        orm_mode = True


class AddProductDelivery(BaseModel):
    product_id: str
    delivery_id: str


class CashBase(BaseModel):
    user_id: str
    user: CoreUserSimple
    balance: float


class CashUpdate(CashBase):
    balance: float

"""Schemas file for endpoint /amap"""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.groups_type import AmapSlotType


class ProductBase(BaseModel):
    """Base schema for AMAP products"""

    name: str
    price: float


class ProductSimple(ProductBase):
    category: str


class ProductComplete(ProductSimple):
    id: str

    class Config:
        orm_mode = True


class ProductQuantity(ProductSimple):
    quantity: int
    id: str

    class Config:
        orm_mode = True


class DeliveryBase(BaseModel):
    """Base schema for AMAP deliveries"""

    delivery_date: date
    products_ids: list[str] = []


class DeliveryComplete(DeliveryBase):
    id: str

    class Config:
        orm_mode = True


class DeliveryReturn(BaseModel):
    delivery_date: date
    products: list[ProductComplete] = []
    id: str

    class Config:
        orm_mode = True


class OrderBase(BaseModel):
    user_id: str
    delivery_id: str
    products_ids: list[str]
    collection_slot: AmapSlotType
    delivery_date: date
    products_quantity: list[int]


class OrderComplete(OrderBase):
    order_id: str
    amount: float
    ordering_date: datetime

    class Config:
        orm_mode = True


class OrderReturn(BaseModel):
    user_id: str
    delivery_id: str
    products: list[ProductQuantity]
    collection_slot: AmapSlotType
    delivery_date: date
    order_id: str
    amount: float
    ordering_date: datetime

    class Config:
        orm_mode = True


class OrderEdit(OrderBase):
    order_id: str

    class Config:
        orm_mode = True


class AddProductDelivery(BaseModel):
    product_id: str
    delivery_id: str


class CashBase(BaseModel):
    balance: float


class CashId(CashBase):
    user_id: str


class CashComplete(CashId):
    user: CoreUserSimple

    class Config:
        orm_mode = True

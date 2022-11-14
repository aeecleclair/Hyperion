"""Schemas file for endpoint /amap"""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.amap_types import AmapSlotType


class Rights(BaseModel):
    view: bool
    manage: bool
    amap_id: str

    class Config:
        orm_mode = True


class ProductBase(BaseModel):
    """Base schema for AMAP products"""

    name: str
    price: float


class ProductSimple(ProductBase):
    category: str


class ProductEdit(BaseModel):
    category: str | None = None
    name: str | None = None
    price: float | None = None


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
    locked: bool = False


class DeliveryComplete(DeliveryBase):
    id: str

    class Config:
        orm_mode = True


class DeliveryReturn(BaseModel):
    delivery_date: date
    products: list[ProductComplete] = []
    id: str
    locked: bool

    class Config:
        orm_mode = True


class DeliveryUpdate(BaseModel):
    delivery_date: date | None = None
    locked: bool | None = None


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
    user: CoreUserSimple
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

    class Config:
        orm_mode = True


class CashComplete(CashBase):
    user: CoreUserSimple


class CashDB(CashBase):
    user_id: str

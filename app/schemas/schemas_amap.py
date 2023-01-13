"""Schemas file for endpoint /amap"""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.amap_types import AmapSlotType, DeliveryStatusType


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
    product: ProductComplete

    class Config:
        orm_mode = True


class DeliveryBase(BaseModel):
    """Base schema for AMAP deliveries"""

    delivery_date: date
    products_ids: list[str] = []


class DeliveryComplete(DeliveryBase):
    id: str
    status: DeliveryStatusType

    class Config:
        orm_mode = True


class DeliveryUpdate(BaseModel):
    delivery_date: date | None = None


class DeliveryProductsUpdate(BaseModel):
    products_ids: list[str]


class OrderBase(BaseModel):
    user_id: str
    delivery_id: str
    products_ids: list[str]
    collection_slot: AmapSlotType
    products_quantity: list[int]


class OrderComplete(OrderBase):
    order_id: str
    amount: float
    ordering_date: datetime
    delivery_date: date

    class Config:
        orm_mode = True


class OrderReturn(BaseModel):
    user: CoreUserSimple
    delivery_id: str
    productsdetail: list[ProductQuantity]
    collection_slot: AmapSlotType
    order_id: str
    amount: float
    ordering_date: datetime
    dalivery_date: date

    class Config:
        orm_mode = True


class OrderEdit(BaseModel):
    products_ids: list[str] | None = None
    collection_slot: AmapSlotType | None = None
    products_quantity: list[int] | None = None

    class Config:
        orm_mode = True


class DeliveryReturn(BaseModel):
    delivery_date: date
    products: list[ProductComplete] = []
    id: str
    status: DeliveryStatusType

    class Config:
        orm_mode = True


class AddProductDelivery(BaseModel):
    product_id: str
    delivery_id: str


class CashBase(BaseModel):
    balance: float
    user_id: str

    class Config:
        orm_mode = True


class CashComplete(CashBase):
    user: CoreUserSimple


class CashDB(CashBase):
    user_id: str


class CashEdit(BaseModel):
    balance: float

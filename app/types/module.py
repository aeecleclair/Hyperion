from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.schemas_notification import Topic
from app.core.payment import schemas_payment
from app.types.factory import Factory


class CoreModule:
    def __init__(
        self,
        root: str,
        tag: str,
        factory: Factory | None,
        router: APIRouter | None = None,
        payment_callback: Callable[
            [schemas_payment.CheckoutPayment, AsyncSession],
            Awaitable[None],
        ]
        | None = None,
        registred_topics: list[Topic] | None = None,
    ):
        """
        Initialize a new Module object.
        :param root: the root of the module, used by Titan
        :param tag: the tag of the module, used by FastAPI
        :param factory: a factory to use to create fake data for the module (development purpose)
        :param router: an optional custom APIRouter
        :param payment_callback: an optional method to call when a payment is notified by HelloAsso. A CheckoutPayment and the database will be provided during the call
        :param registred_topics: an optionnal list of Topics that should be registered by the module. Modules can also register topics dynamically.
            Once the Topic was registred, removing it from this list won't delete it
        """
        self.root = root
        self.router = router or APIRouter(tags=[tag])
        self.payment_callback: (
            Callable[[schemas_payment.CheckoutPayment, AsyncSession], Awaitable[None]]
            | None
        ) = payment_callback
        self.registred_topics = registred_topics
        self.factory = factory


class Module(CoreModule):
    def __init__(
        self,
        root: str,
        tag: str,
        factory: Factory | None,
        default_allowed_groups_ids: list[GroupType] | None = None,
        default_allowed_account_types: list[AccountType] | None = None,
        router: APIRouter | None = None,
        payment_callback: Callable[
            [schemas_payment.CheckoutPayment, AsyncSession],
            Awaitable[None],
        ]
        | None = None,
        registred_topics: list[Topic] | None = None,
    ):
        """
        Initialize a new Module object.
        :param root: the root of the module, used by Titan
        :param tag: the tag of the module, used by FastAPI
        :param factory: a factory to use to create fake data for the module (development purpose)
        :param default_allowed_groups_ids: list of groups that should be able to see the module by default
        :param default_allowed_account_types: list of account_types that should be able to see the module by default
        :param router: an optional custom APIRouter
        :param payment_callback: an optional method to call when a payment is notified by HelloAsso. A CheckoutPayment and the database will be provided during the call
        :param registred_topics: an optionnal list of Topics that should be registered by the module. Modules can also register topics dynamically.
            Once the Topic was registred, removing it from this list won't delete it
        """
        self.root = root
        self.default_allowed_groups_ids = default_allowed_groups_ids
        self.default_allowed_account_types = default_allowed_account_types
        self.router = router or APIRouter(tags=[tag])
        self.payment_callback: (
            Callable[[schemas_payment.CheckoutPayment, AsyncSession], Awaitable[None]]
            | None
        ) = payment_callback
        self.registred_topics = registred_topics
        self.factory = factory

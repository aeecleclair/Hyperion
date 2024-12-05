from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.payment import schemas_payment


class Module:
    def __init__(
        self,
        root: str,
        tag: str,
        default_allowed_groups_ids: list[GroupType] | None = None,
        default_allowed_account_types: list[AccountType] | None = None,
        router: APIRouter | None = None,
        payment_callback: Callable[
            [schemas_payment.CheckoutPayment, AsyncSession],
            Awaitable[None],
        ]
        | None = None,
    ):
        """
        Initialize a new Module object.
        :param root: the root of the module, used by Titan
        :param default_allowed_groups_ids: list of groups that should be able to see the module by default
        :param router: an optional custom APIRouter
        :param payment_callback: an optional method to call when a payment is notified by HelloAsso. A CheckoutPayment and the database will be provided during the call
        """
        self.root = root
        self.default_allowed_groups_ids = default_allowed_groups_ids
        self.default_allowed_account_types = default_allowed_account_types
        self.router = router or APIRouter(tags=[tag])
        self.payment_callback: (
            Callable[[schemas_payment.CheckoutPayment, AsyncSession], Awaitable[None]]
            | None
        ) = payment_callback

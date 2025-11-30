from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cdr.coredata_cdr import CdrYear
from app.modules.cdr.cruds_cdr import get_payments_by_user_id, get_purchases_by_user_id
from app.types.module_user_deleter import ModuleUserDeleter
from app.utils.tools import get_core_data


class CdrUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        reasons = ""
        year = await get_core_data(CdrYear, db)
        purchases = await get_purchases_by_user_id(db, user_id, year.year)
        payments = await get_payments_by_user_id(db, user_id, year.year)
        if any(not purchase.validated for purchase in purchases):
            reasons += "\n   - User has pending purchases"
        if sum(payment.total for payment in payments) != sum(
            purchase.quantity * purchase.product_variant.price for purchase in purchases
        ):
            reasons += "\n   - User has uneven wallet balance"
        return reasons

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass

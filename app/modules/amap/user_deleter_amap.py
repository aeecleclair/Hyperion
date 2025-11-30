from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.amap import cruds_amap
from app.modules.amap.types_amap import DeliveryStatusType
from app.types.module_user_deleter import ModuleUserDeleter


class AmapUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        # Check if the user has any active orders or a negative balance
        reasons = []
        user_cash = await cruds_amap.get_cash_by_id(user_id=user_id, db=db)
        if user_cash is not None:
            if user_cash.balance < 0:
                reasons.append("User has negative balance")
        orders = await cruds_amap.get_orders_of_user(user_id=user_id, db=db)
        for order in orders:
            delivery = await cruds_amap.get_delivery_by_id(
                db=db,
                delivery_id=order.delivery_id,
            )
            if delivery is None:
                continue
            if delivery.status not in [
                DeliveryStatusType.delivered,
                DeliveryStatusType.archived,
            ]:
                reasons.append(
                    f"User has order in delivery not delivered or archived: {order.delivery_id}",
                )
        if reasons:
            return "\n   - ".join(reasons)
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass

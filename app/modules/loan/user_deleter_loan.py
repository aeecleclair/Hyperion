from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.loan.cruds_loan import get_loans_by_borrower
from app.types.module_user_deleter import ModuleUserDeleter


class LoanUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        loans = await get_loans_by_borrower(db, user_id)
        if any(not loan.returned for loan in loans):
            return "\n   - User has pending loans"
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass

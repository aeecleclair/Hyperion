from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import schemas_auth
from app.core.auth.dependencies_auth import filter_user_token
from app.core.mypayment.coredata_mypayment import MyPaymentBankAccountHolder
from app.core.mypayment.cruds_mypayment import get_structure_by_id
from app.dependencies import get_db
from app.utils.tools import get_core_data


async def is_user_bank_account_holder(
    token: schemas_auth.TokenData = Depends(filter_user_token()),
    db: AsyncSession = Depends(get_db),
) -> schemas_auth.TokenData:
    """Check if the user is a bank account holder."""
    account_holder = await get_core_data(
        MyPaymentBankAccountHolder,
        db=db,
    )
    structure = await get_structure_by_id(
        db=db,
        structure_id=account_holder.holder_structure_id,
    )
    if not structure:
        raise HTTPException(
            status_code=404,
            detail="Structure not found for the bank account holder",
        )
    if structure.manager_user_id != token.id:
        raise HTTPException(
            status_code=403,
            detail="User is not the bank account holder",
        )
    return token

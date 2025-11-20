from uuid import UUID

from app.types.core_data import BaseCoreData


class MyECLPayBankAccountHolder(BaseCoreData):
    """Bank account holder information for MyECLPay."""

    holder_structure_id: UUID

from uuid import UUID

from app.types.core_data import BaseCoreData


class MyPaymentBankAccountHolder(BaseCoreData):
    """Bank account holder information for MyPayment."""

    holder_structure_id: UUID

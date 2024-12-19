from app.core.myeclpay.types_myeclpay import StoreStructure
from app.types.core_data import BaseCoreData


class StoreStructuresUser(BaseCoreData):
    """
    Schema defining the stores manager for each association
    """

    managers: dict[StoreStructure, str] = {}

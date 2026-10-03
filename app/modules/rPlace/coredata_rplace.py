from app.types.core_data import BaseCoreData


class gridInformation(BaseCoreData):
    nbLigne: int = 100
    nbColonne: int = 100
    pixelSize: float = 10
    cooldown: int = 10000000

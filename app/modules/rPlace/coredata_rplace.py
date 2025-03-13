from app.types import core_data

class gridInformation(core_data.BaseCoreData):
    nbLigne: int = 100
    nbColonne: int = 100
    pixelSize: float = 10
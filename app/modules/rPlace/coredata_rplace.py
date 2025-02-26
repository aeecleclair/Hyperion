from app.types import core_data

class gridInformation(core_data.BaseCoreData):
    nbLigne: int = 500
    nbColonne: int = 500
    pixelSize: float = 10
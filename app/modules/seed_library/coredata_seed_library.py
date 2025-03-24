from app.types.core_data import BaseCoreData


class SeedLibraryInformation(BaseCoreData):
    facebook_url: str = ""
    forum_url: str = ""
    description: str = ""  # pour expliquer le principe du module
    contact: str = ""

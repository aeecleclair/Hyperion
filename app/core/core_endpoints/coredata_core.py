from app.types.core_data import BaseCoreData


class ModuleVisibilityAwareness(BaseCoreData):
    """
    Schema for module visibility awareness
    """

    roots: list[str] = []

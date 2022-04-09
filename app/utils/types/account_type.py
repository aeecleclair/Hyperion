from enum import Enum


class AccountType(str, Enum):
    """
    Various account type that can be created in Hyperion
    """

    eleve = "Élève"
    personnel = "Personnel"
    association = "Association"

from enum import Enum


class IndividualCategoryType(str, Enum):
    pe = "pe"
    pa = "pa"
    autre = "autre"
    tfe = "tfe"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"


class RoleType(str, Enum):
    prez = "prez"
    trez = "trez"
    trez_int = "trez_int"
    trez_ext = "trez_ext"
    sg = "sg"
    com = "com"
    profs = "profs"
    matos = "matos"
    appro = "appro"
    te = "te"
    projets = "projets"
    boutique = "boutique"
    perms = "perms"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"


class AssociationStructureType(str, Enum):
    asso = "asso"
    club = "club"
    section = "section"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"


class AssociationType(str, Enum):
    aeecl = "aeecl"
    useecl = "useecl"
    independant = "independant"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"

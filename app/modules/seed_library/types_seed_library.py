from enum import Enum


class SpeciesType(Enum):
    aromatic = "Plantes aromatiques"
    vegetables = "Plantes potagères"
    interior = "Plante d intérieur"
    fruit = "Plantes fruitières"
    cactus = "Cactus et succulentes"
    ornamental = "Plantes ornementales"
    succulent = "Plantes grasses"
    other = "Autre"


class State(Enum):
    waiting = "en attente"
    retrieved = "récupérée"
    used_up = "consommée"


class PropagationMethod(Enum):
    cutting = "bouture"
    seed = "graine"

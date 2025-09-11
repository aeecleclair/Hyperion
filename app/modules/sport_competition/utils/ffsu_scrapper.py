import logging

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.modules.sport_competition import (
    schemas_sport_competition,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


class FFSUData(BaseModel):
    licenses: list[str]
    name: str
    firstname: str
    sport_without_constraints: str
    sport_with_constraints: str


def scrap_ffsu_licenses(
    school_ffsu_id: str,
    user_name: str,
    user_firstname: str,
) -> list[FFSUData]:
    """
    Scrape the FFSU information from the user's profile.
    """

    url = "https://www.sport-u-licenses.com/sport-u/resultat.php"

    data = {
        "NUMAS": school_ffsu_id,
        "NOM": user_name,
        "PRENOM": user_firstname,
        "SPORT": "tous",
        "SUBMIT": "Valider",
    }

    response = requests.post(url, data=data, timeout=10)
    soup = BeautifulSoup(response.content, "html.parser")

    # Récupération dynamique des données présentes aux emplacements ciblés
    target_rows = soup.find_all("tr")[
        2:
    ]  # Le tableau cible est à la 3ème ligne du bloc <tr>
    # On récupère toutes les cellules de la ligne sélectionnée
    result: list[FFSUData] = []
    for target_row in target_rows:
        cells = target_row.find_all("td")  # type: ignore[union-attr]
        if len(cells) < 11:
            continue
        result.append(
            FFSUData(
                licenses=cells[0].get_text(strip=True).split(" "),
                name=cells[4].get_text(strip=True),
                firstname=cells[5].get_text(strip=True),
                sport_without_constraints=cells[9].get_text(strip=True),
                sport_with_constraints=cells[10].get_text(strip=True),
            ),
        )

    # Création d'une liste générique avec les valeurs textuelles stripées
    return result


def validate_participant_ffsu_license(
    school: schemas_sport_competition.SchoolExtension,
    user: schemas_sport_competition.CompetitionUser,
    ffsu_license: str,
):
    try:
        ffsu_data = scrap_ffsu_licenses(
            school.ffsu_id or "",
            user.user.firstname,
            user.user.name,
        )
    except Exception:
        hyperion_error_logger.exception(
            f"Error while scraping FFSU data for user {user.user.id}",
        )
        return False
    return any(ffsu_license in data.licenses for data in ffsu_data)

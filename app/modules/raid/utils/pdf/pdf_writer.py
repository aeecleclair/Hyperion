import io
import logging
import pathlib
from pathlib import Path
from typing import cast

import fitz
from fastapi.templating import Jinja2Templates
from fpdf import FPDF, Align, XPos, YPos
from fpdf.enums import TableCellFillMode, VAlign
from fpdf.fonts import FontFace
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from pypdf import PdfReader, PdfWriter

from app.modules.raid import coredata_raid
from app.modules.raid.models_raid import Document, Participant, SecurityFile, Team
from app.modules.raid.utils.pdf.conversion_utils import (
    date_to_string,
    get_difficulty_label,
    get_document_label,
    get_document_validation_label,
    get_meeting_place_label,
    get_situation_label,
    get_size_label,
    nullable_number_to_string,
)
from app.utils.tools import get_file_path_from_data

templates = Jinja2Templates(directory="assets/templates")

hyperion_error_logger = logging.getLogger("hyperion.error")


def maximize_image(
    image_path: Path,
    max_width: float,
    max_height: float,
) -> Image.Image:
    image = cast("Image.Image", Image.open(image_path))
    width, height = image.size
    if width > height:
        image = image.rotate(270, expand=True)
    image.thumbnail((max_width, max_height), resample=Image.Resampling.BILINEAR)
    return image


class PDFWriter(FPDF):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pdf_pages: list[int] = []

    def header(self):
        if self.page_no() - 1 not in self.pdf_pages:
            self.set_font("times", "B", 20)
            self.cell(
                w=0,
                h=10,
                text=f"Dossier d'inscription de l'équipe {self.team.name}",
                align="C",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

    def add_pdf(self) -> str:
        reader = PdfReader(io.BytesIO(self.output()))
        for i in range(len(self.pdf_paths)):
            path = get_file_path_from_data(
                "raid",
                self.pdf_paths[i],
                "assets/pdf/default_pdf.pdf",
            )
            pages = PdfReader(path).pages
            for j, page in enumerate(pages):
                reader.pages[self.pdf_indexes[i] + j].merge_page(page2=page)

        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.write("data/raid/" + self.file_name)
        return "data/raid/" + self.file_name

    def footer(self):
        if self.page_no() - 1 not in self.pdf_pages:
            self.set_y(-15)
            self.set_font("times", "I", 8)
            self.cell(
                w=0,
                h=10,
                text=f"Page {self.page_no()} - Raid Centrale Lyon",
                align="C",
                new_x=XPos.LMARGIN,
                new_y=YPos.BMARGIN,
            )

    def write_team(self, team: Team) -> str:
        self.pdf_indexes: list[int] = []
        self.pdf_paths: list[str] = []
        self.pdf_pages = []
        self.team = team
        self.file_name = (
            str(team.number) + "_" if team.number else ""
        ) + f"{team.name}_{team.captain.name}_{team.captain.firstname}.pdf"
        self.add_page()
        self.write_team_summary(team)
        self.write_participant_summary(team.captain)
        if team.second:
            self.write_participant_summary(team.second, is_second=True)
        else:
            self.write_empty_participant()
        if team.captain.security_file:
            self.write_security_file(team.captain.security_file, team.captain)
        self.write_participant_document(team.captain)
        if team.second:
            if team.second.security_file:
                self.write_security_file(team.second.security_file, team.second)
            self.write_participant_document(team.second)
        return self.add_pdf()

    def clear_pdf(self):
        Path("data/raid/" + self.file_name).unlink()
        self = PDFWriter()  # noqa: PLW0642

    def write_empty_participant(self):
        self.set_font("times", "B", 12)
        self.set_y(self.get_y() + 4)
        self.cell(
            w=0,
            h=12,
            text="Coéquipier",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("times", "", 12)
        self.cell(
            w=0,
            h=10,
            text="Non renseigné",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def write_participant_document(self, participant: Participant):
        for document in [
            participant.id_card,
            participant.medical_certificate,
            participant.student_card,
            participant.raid_rules,
            participant.parent_authorization,
        ]:
            if document:
                pdf = get_file_path_from_data("raid", document.id, "documents")
                extension = pdf.absolute().suffix[1:]
                if extension in ["jpg", "jpeg", "png"]:
                    self.write_document(document, participant)
                else:
                    self.write_document_header(document, participant)
                    self.pdf_indexes.append(self.page_no())
                    number_page = len(PdfReader(pdf).pages)
                    self.pdf_pages.extend(
                        list(range(self.page_no(), self.page_no() + number_page)),
                    )
                    for _ in range(number_page):
                        self.add_page()
                    self.pdf_paths.append(document.id)

    def write_document_header(self, document: Document, participant: Participant):
        self.add_page()
        self.set_y(self.get_y() + 6)
        self.set_font("times", "B", 12)
        self.cell(
            w=0,
            h=4,
            text=f"{get_document_label(document.type)} de {participant.firstname} {participant.name}",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("times", "", 12)
        data = [
            ["Date de téléversement", "Validé"],
            [
                date_to_string(document.uploaded_at),
                get_document_validation_label(document.validation),
            ],
        ]
        self.set_y(self.get_y() + 6)

        self.set_draw_color(255, 255, 255)
        self.set_line_width(0)
        with self.table(
            borders_layout="NONE",
            cell_fill_mode=TableCellFillMode.NONE,
            line_height=6,
            text_align="CENTER",
            v_align=VAlign.M,
        ) as table:  # type: ignore[call-arg]
            for data_row in data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def write_security_file(
        self,
        security_file: SecurityFile,
        participant: Participant,
    ):
        self.add_page()
        self.set_y(self.get_y() + 6)
        self.set_font("times", "B", 12)
        self.cell(
            w=0,
            h=4,
            text=f"Fiche Sécurité de {participant.firstname} {participant.name}",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("times", "", 12)
        data: list[list[str] | None] = [
            ["Allergie", security_file.allergy if security_file.allergy else "Aucune"],
            ["Asthme", (security_file.asthma and "Oui") or "Non"],
            (
                [
                    "Service de réanimation",
                    (security_file.intensive_care_unit and "Oui") or "Non",
                ]
                if security_file.allergy
                else None
            ),
            (
                [
                    "Date du service de réanimation",
                    security_file.intensive_care_unit_when
                    if security_file.intensive_care_unit_when
                    else "Non renseignée",
                ]
                if security_file.intensive_care_unit
                else None
            ),
            [
                "Traitement en cours",
                (
                    security_file.ongoing_treatment
                    if security_file.ongoing_treatment
                    else "Aucun"
                ),
            ],
            [
                "Maladies",
                security_file.sicknesses if security_file.sicknesses else "Aucune",
            ],
            [
                "Hospitalisation",
                (
                    security_file.hospitalization
                    if security_file.hospitalization
                    else "Aucune"
                ),
            ],
            [
                "Opération chirurgicale",
                (
                    security_file.surgical_operation
                    if security_file.surgical_operation
                    else "Aucune"
                ),
            ],
            ["Traumatisme", security_file.trauma if security_file.trauma else "Aucun"],
            [
                "Antécédents familiaux",
                security_file.family if security_file.family else "Aucun",
            ],
        ]
        for data_row in data:
            if data_row:
                self.write_key_label(data_row[0], data_row[1])

        self.set_y(self.get_y() + 6)
        self.set_font("times", "B", 12)
        self.cell(
            w=0,
            h=4,
            text="Personne à contacter en cas d'urgence",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("times", "", 12)
        data = [
            [
                "Prénom",
                security_file.emergency_person_firstname
                if security_file.emergency_person_firstname
                else "Non renseigné",
            ],
            [
                "Nom",
                security_file.emergency_person_name
                if security_file.emergency_person_name
                else "Non renseigné",
            ],
            [
                "Téléphone",
                security_file.emergency_person_phone
                if security_file.emergency_person_phone
                else "Non renseigné",
            ],
        ]
        for data_row in data:
            if data_row:
                self.write_key_label(data_row[0], data_row[1])

    def write_document(self, document: Document, participant: Participant):
        self.write_document_header(document, participant)
        self.set_y(self.get_y() + 6)
        file = get_file_path_from_data("raid", document.id, "documents")
        image = maximize_image(file, self.epw * 2.85, (self.eph - 45) * 2.85)
        image_width, _ = image.size
        x = ((self.epw * 2.85 - image_width) / 2) / 2.85 + 10
        self.image(image, x=x)

    def write_team_summary(self, team: Team):
        self.set_font("times", "", 12)
        data = [
            ["Parcours", "Lieu de rendez-vous", "Numéro", "Inscription"],
            [
                get_difficulty_label(team.difficulty),
                get_meeting_place_label(team.meeting_place),
                nullable_number_to_string(team.number),
                str(int(team.validation_progress)) + " %",
            ],
        ]
        self.set_y(self.get_y() + 6)

        self.set_draw_color(255, 255, 255)
        self.set_line_width(0)
        with self.table(
            borders_layout="NONE",
            cell_fill_mode=TableCellFillMode.NONE,
            line_height=6,
            text_align="CENTER",
            v_align=VAlign.M,
        ) as table:  # type: ignore[call-arg]
            for data_row in data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def write_participant_summary(
        self,
        participant: Participant,
        is_second: bool = False,
    ):
        self.set_font("times", "B", 12)
        self.set_y(self.get_y() + 4)
        self.cell(
            w=0,
            h=12,
            text=(is_second and "Coéquipier") or "Capitaine",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("times", "", 12)
        data: list[list[str] | None] = [
            ["Nom", participant.name],
            ["Prénom", participant.firstname],
            ["Date de naissance", date_to_string(participant.birthday)],
            [
                "Adresse",
                participant.address if participant.address else "Non renseignée",
            ],
            ["Téléphone", participant.phone],
            ["Email", participant.email],
            ["Taille du vélo", get_size_label(participant.bike_size)],
            [
                "Taille du t-shirt",
                get_size_label(participant.t_shirt_size) + " (payé)"
                if participant.t_shirt_payment
                else " (non payé)",
            ],
            ["Situation", get_situation_label(participant.situation)],
            ["Ecole", participant.other_school] if participant.other_school else None,
            ["Entreprise", participant.company] if participant.company else None,
            ["Régime alimentaire", participant.diet if participant.diet else "Aucun"],
            [
                "Attestation sur l'honneur",
                "Oui" if participant.attestation_on_honour else "Non",
            ],
            [
                "Documents validés",
                f"{participant.number_of_validated_document}/{participant.number_of_document}",
            ],
            [
                "Paiement",
                "Oui" if participant.payment else "Non",
            ],
        ]
        for data_row in data:
            if data_row:
                self.write_key_label(data_row[0], data_row[1])

    def write_key_label(self, key: str, label: str):
        headings_style = FontFace(emphasis="")
        with self.table(
            borders_layout="NONE",
            cell_fill_mode=TableCellFillMode.NONE,
            line_height=8,
            text_align=Align.J,
            v_align=VAlign.M,
            headings_style=headings_style,
        ) as table:  # type: ignore[call-arg]
            row = table.row()
            row.cell(key)
            row.cell(label)


class HTMLPDFWriter:
    def __init__(self):
        self.html = ""

    def write_participant_security_file(
        self,
        participant: Participant,
        information: coredata_raid.RaidInformation,
        team_number: int | None,
    ):
        environment = Environment(
            loader=FileSystemLoader("assets/templates"),
            autoescape=select_autoescape(["html"]),
        )
        results_template = environment.get_template("template.html")

        context = {
            **participant.__dict__,
            "information": {
                "president": information.president.__dict__
                if information.president
                else None,
                "rescue": information.rescue.__dict__ if information.rescue else None,
                "security_responsible": information.security_responsible.__dict__
                if information.security_responsible
                else None,
                "volunteer_responsible": information.volunteer_responsible.__dict__
                if information.volunteer_responsible
                else None,
            },
            "team_number": team_number,
        }
        html_content = results_template.render(context)
        csspath = pathlib.Path("assets/templates/style.css")
        css_content = csspath.read_bytes().decode()
        story = fitz.Story(html=html_content, user_css=css_content, em=10)
        writer = fitz.DocumentWriter("data/raid/" + participant.id + ".pdf")
        mediabox = fitz.paper_rect("a4")
        where = mediabox + (36, 36, -36, -36)  # noqa: RUF005

        more = True
        while more:
            page = writer.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(page)
            writer.end_page()
        writer.close()
        return "data/raid/" + participant.id + ".pdf"

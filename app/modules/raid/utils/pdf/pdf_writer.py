import io
import os

from fpdf import FPDF
from fpdf.enums import TableCellFillMode, VAlign
from fpdf.fonts import FontFace
from PIL import Image
from pypdf import PdfReader, PdfWriter

from app.modules.raid.schemas_raid import Document, Participant, SecurityFile, Team
from app.modules.raid.utils.pdf.conversion_utils import (
    date_to_string,
    get_difficulty_label,
    get_document_label,
    get_meeting_place_label,
    get_situation_label,
    get_size_label,
    nullable_number_to_string,
)


def maximize_image(image_path: str, max_width: int, max_height: int) -> Image:
    image = Image.open(image_path)
    width, height = image.size
    if width > height:
        image = image.rotate(270, expand=True)
    image.thumbnail((max_width, max_height), resample=Image.BILINEAR)
    return image


class PDFWriter(FPDF):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def header(self):
        if self.page_no() - 1 not in self.pdf_pages:
            self.set_font("times", "B", 20)
            self.cell(
                0, 10, f"Dossier d'inscription de l'équipe {self.team.name}", 0, 1, "C"
            )

    def add_pdf(self):
        reader = PdfReader(io.BytesIO(self.output()))
        for i in range(len(self.pdf_paths)):
            pages = PdfReader(self.pdf_paths[i]).pages
            for j, page in enumerate(pages):
                reader.pages[self.pdf_indexes[i] + j].merge_page(page2=page)

        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.write(self.file_name)

    def footer(self):
        if self.page_no() - 1 not in self.pdf_pages:
            self.set_y(-15)
            self.set_font("times", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()} - Raid Centrale Lyon", 0, 0, "C")

    def write_team(self, team: Team) -> str:
        self.pdf_indexes = []
        self.pdf_pages = []
        self.pdf_paths = []
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
        self.add_pdf()

    def clear_pdf(self):
        os.Path.unlink(self.file_name)

    def write_empty_participant(self):
        self.set_font("times", "B", 12)
        self.ln(4)
        self.cell(0, 12, "Coéquipier", 0, 1, "L")
        self.set_font("times", "", 12)
        self.cell(0, 10, "Non renseigné", 0, 1, "C")

    def write_participant_document(self, participant: Participant):
        for document in [
            participant.id_card,
            participant.medical_certificate,
            participant.student_card,
            participant.raid_rules,
        ]:
            if document:
                extension = document.id.split(".")[-1]
                if extension in ["jpg", "jpeg", "png"]:
                    self.write_document(document, participant)
                else:
                    self.write_document_header(document, participant)
                    self.pdf_indexes.append(self.page_no())
                    number_page = len(PdfReader(document.id).pages)
                    self.pdf_pages.extend(
                        list(range(self.page_no(), self.page_no() + number_page))
                    )
                    for _ in range(number_page):
                        self.add_page()
                    self.pdf_paths.append(document.id)

    def write_document_header(self, document: Document, participant: Participant):
        self.add_page()
        self.ln(6)
        self.set_font("times", "B", 12)
        self.cell(
            0,
            4,
            f"{get_document_label(document.type)} de {participant.firstname} {participant.name}",
            0,
            1,
            "C",
        )
        self.set_font("times", "", 12)
        data = [
            ["Date de téléversement", "Validé"],
            [
                date_to_string(document.uploaded_at),
                document.validated and "Oui" or "Non",
            ],
        ]
        self.ln(6)

        self.set_draw_color(255, 255, 255)
        self.set_line_width(0)
        with self.table(
            borders_layout="NONE",
            cell_fill_mode=TableCellFillMode.NONE,
            line_height=6,
            text_align="CENTER",
            v_align=VAlign.M,
        ) as table:
            for data_row in data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def write_security_file(
        self, security_file: SecurityFile, participant: Participant
    ):
        self.add_page()
        self.ln(6)
        self.set_font("times", "B", 12)
        self.cell(
            0,
            4,
            f"Fiche Sécurité de {participant.firstname} {participant.name}",
            0,
            1,
            "C",
        )
        self.set_font("times", "", 12)
        data = [
            ["Allergie", security_file.allergy if security_file.allergy else "Aucune"],
            ["Asthme", security_file.asthma and "Oui" or "Non"],
            (
                [
                    "Service de réanimation",
                    security_file.intensive_care_unit and "Oui" or "Non",
                ]
                if security_file.intensive_care_unit
                else None
            ),
            (
                [
                    "Date du service de réanimation",
                    security_file.intensive_care_unit_when,
                ]
                if security_file.intensive_care_unit_when
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

    def write_document(self, document: Document, participant: Participant):
        self.write_document_header(document, participant)
        self.ln(6)
        image = maximize_image(document.id, self.epw * 2.85, (self.eph - 45) * 2.85)
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
                str(int(team.validation_progress * 100)) + " %",
            ],
        ]
        self.ln(6)

        self.set_draw_color(255, 255, 255)
        self.set_line_width(0)
        with self.table(
            borders_layout="NONE",
            cell_fill_mode=TableCellFillMode.NONE,
            line_height=6,
            text_align="CENTER",
            v_align=VAlign.M,
        ) as table:
            for data_row in data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def write_participant_summary(
        self, participant: Participant, is_second: bool = False
    ):
        self.set_font("times", "B", 12)
        self.ln(4)
        self.cell(0, 12, is_second and "Coéquipier" or "Capitaine", 0, 1, "L")
        self.set_font("times", "", 12)
        data = [
            ["Nom", participant.name],
            ["Prénom", participant.firstname],
            ["Date de naissance", date_to_string(participant.birthday)],
            ["Adresse", participant.address],
            ["Téléphone", participant.phone],
            ["Email", participant.email],
            ["Taille du vélo", get_size_label(participant.bike_size)],
            ["Taille du t-shirt", get_size_label(participant.t_shirt_size)],
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
            line_height=7.8,
            text_align=("LEFT", "RIGHT"),
            v_align=VAlign.M,
            headings_style=headings_style,
        ) as table:
            row = table.row()
            row.cell(key)
            row.cell(label)

from datetime import date

from app.modules.raid.schemas_raid import EmergencyContact
from app.types import core_data


class RaidInformation(core_data.BaseCoreData):
    raid_start_date: date | None = None
    raid_end_date: date | None = None
    raid_registering_end_date: date | None = None
    payment_link: str | None = None
    contact: str | None = None
    president: EmergencyContact | None = None
    volunteer_responsible: EmergencyContact | None = None
    security_responsible: EmergencyContact | None = None
    rescue: EmergencyContact | None = None
    raid_rules_id: str | None = None
    raid_information_id: str | None = None


class RaidDriveFolders(core_data.BaseCoreData):
    parent_folder_id: str | None = None
    registering_folder_id: str | None = None
    security_folder_id: str | None = None


class RaidPrice(core_data.BaseCoreData):
    student_price: int | None = None
    partner_price: int | None = None
    external_price: int | None = None
    t_shirt_price: int | None = None

from app.core.permissions.type_permissions import ModulePermissions


class SportCompetitionPermissions(ModulePermissions):
    access_sport_competition = "access_sport_competition"
    manage_sport_competition = "manage_sport_competition"
    volunteer_sport_competition = "volunteer_sport_competition"

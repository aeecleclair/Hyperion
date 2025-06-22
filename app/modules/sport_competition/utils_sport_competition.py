from app.core.schools import schemas_schools
from app.modules.sport_competition import (
    models_sport_competition,
    schemas_sport_competition,
)


def school_extension_model_to_schema(
    school_extension: models_sport_competition.SchoolExtension,
) -> schemas_sport_competition.SchoolExtension:
    return schemas_sport_competition.SchoolExtension(
        school_id=school_extension.school_id,
        from_lyon=school_extension.from_lyon,
        active=school_extension.active,
        inscription_enabled=school_extension.inscription_enabled,
        school=schemas_schools.CoreSchool(
            id=school_extension.school.id,
            name=school_extension.school.name,
            email_regex=school_extension.school.email_regex,
        ),
        general_quota=schemas_sport_competition.SchoolGeneralQuota(
            school_id=school_extension.school_id,
            edition_id=school_extension.general_quota.edition_id,
            athlete_quota=school_extension.general_quota.athlete_quota,
            cameraman_quota=school_extension.general_quota.cameraman_quota,
            pompom_quota=school_extension.general_quota.pompom_quota,
            fanfare_quota=school_extension.general_quota.fanfare_quota,
            non_athlete_quota=school_extension.general_quota.non_athlete_quota,
        ),
    )


def participant_complete_model_to_schema(
    participant: models_sport_competition.CompetitionParticipant,
) -> schemas_sport_competition.ParticipantComplete:
    return schemas_sport_competition.ParticipantComplete(
        user_id=participant.user_id,
        sport_id=participant.sport_id,
        edition_id=participant.edition_id,
        team_id=participant.team_id,
        school_id=participant.school_id,
        substitute=participant.substitute,
        license=participant.license,
        user=schemas_sport_competition.CompetitionUser(
            id=participant.user.user_id,
            edition_id=participant.user.edition_id,
            account_type=participant.user.user.account_type,
            school_id=participant.user.user.school_id,
            email=participant.user.user.email,
            name=participant.user.user.name,
            firstname=participant.user.user.firstname,
            phone=participant.user.user.phone,
            validated=participant.user.validated,
            created_at=participant.user.created_at,
        ),
    )


def team_model_to_schema(
    team: models_sport_competition.CompetitionTeam,
) -> schemas_sport_competition.TeamComplete:
    return schemas_sport_competition.TeamComplete(
        id=team.id,
        name=team.name,
        edition_id=team.edition_id,
        school_id=team.school_id,
        sport_id=team.sport_id,
        captain_id=team.captain_id,
        created_at=team.created_at,
        participants=[
            participant_complete_model_to_schema(participant)
            for participant in team.participants
        ],
    )


def match_model_to_schema(
    match: models_sport_competition.Match,
) -> schemas_sport_competition.Match:
    return schemas_sport_competition.Match(
        id=match.id,
        sport_id=match.sport_id,
        edition_id=match.edition_id,
        name=match.name,
        team1_id=match.team1_id,
        team2_id=match.team2_id,
        date=match.date,
        location=match.location,
        score_team1=match.score_team1,
        score_team2=match.score_team2,
        winner_id=match.winner_id,
        team1=schemas_sport_competition.Team(
            name=match.team1.name,
            school_id=match.team1.school_id,
            sport_id=match.team1.sport_id,
            edition_id=match.team1.edition_id,
            captain_id=match.team1.captain_id,
            id=match.team1.id,
            created_at=match.team1.created_at,
        ),
        team2=schemas_sport_competition.Team(
            name=match.team2.name,
            school_id=match.team2.school_id,
            sport_id=match.team2.sport_id,
            edition_id=match.team2.edition_id,
            captain_id=match.team2.captain_id,
            id=match.team2.id,
            created_at=match.team2.created_at,
        ),
    )

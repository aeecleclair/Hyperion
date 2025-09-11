from app.core.users import schemas_users
from app.modules.sport_competition import (
    models_sport_competition,
    schemas_sport_competition,
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
        validated=participant.validated,
        user=schemas_users.CoreUser(
            id=participant.user.id,
            account_type=participant.user.account_type,
            school_id=participant.user.school_id,
            email=participant.user.email,
            name=participant.user.name,
            firstname=participant.user.firstname,
            phone=participant.user.phone,
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
        ),
        team2=schemas_sport_competition.Team(
            name=match.team2.name,
            school_id=match.team2.school_id,
            sport_id=match.team2.sport_id,
            edition_id=match.team2.edition_id,
            captain_id=match.team2.captain_id,
            id=match.team2.id,
        ),
    )

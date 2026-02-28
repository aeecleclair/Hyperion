from app.core.groups import schemas_groups
from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition import (
    models_sport_competition,
    schemas_sport_competition,
)


def competition_user_model_to_schema(
    user: models_sport_competition.CompetitionUser,
) -> schemas_sport_competition.CompetitionUser:
    return schemas_sport_competition.CompetitionUser(
        user_id=user.user_id,
        edition_id=user.edition_id,
        is_athlete=user.is_athlete,
        is_cameraman=user.is_cameraman,
        is_pompom=user.is_pompom,
        is_fanfare=user.is_fanfare,
        is_volunteer=user.is_volunteer,
        allow_pictures=user.allow_pictures,
        validated=user.validated,
        created_at=user.created_at,
        sport_category=user.sport_category,
        user=schemas_users.CoreUser(
            id=user.user.id,
            account_type=user.user.account_type,
            school_id=user.user.school_id,
            email=user.user.email,
            name=user.user.name,
            firstname=user.user.firstname,
            phone=user.user.phone,
            groups=[
                schemas_groups.CoreGroup(
                    id=group.id,
                    name=group.name,
                )
                for group in user.user.groups
            ],
        ),
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
        certificate_file_id=participant.certificate_file_id,
        is_license_valid=participant.is_license_valid,
        user=competition_user_model_to_schema(participant.user),
        team=schemas_sport_competition.Team(
            id=participant.team.id,
            name=participant.team.name,
            edition_id=participant.team.edition_id,
            school_id=participant.team.school_id,
            sport_id=participant.team.sport_id,
            captain_id=participant.team.captain_id,
            created_at=participant.team.created_at,
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
) -> schemas_sport_competition.MatchComplete:
    return schemas_sport_competition.MatchComplete(
        id=match.id,
        sport_id=match.sport_id,
        edition_id=match.edition_id,
        name=match.name,
        team1_id=match.team1_id,
        team2_id=match.team2_id,
        date=match.date,
        location_id=match.location_id,
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
        location=schemas_sport_competition.Location(
            id=match.location.id,
            name=match.location.name,
            description=match.location.description,
            address=match.location.address,
            latitude=match.location.latitude,
            longitude=match.location.longitude,
            edition_id=match.location.edition_id,
        ),
    )


def purchase_model_to_schema(
    purchase: models_sport_competition.CompetitionPurchase,
) -> schemas_sport_competition.PurchaseComplete:
    return schemas_sport_competition.PurchaseComplete(
        user_id=purchase.user_id,
        product_variant_id=purchase.product_variant_id,
        edition_id=purchase.edition_id,
        quantity=purchase.quantity,
        purchased_on=purchase.purchased_on,
        validated=purchase.validated,
        product_variant=schemas_sport_competition.ProductVariant(
            id=purchase.product_variant.id,
            edition_id=purchase.product_variant.edition_id,
            product_id=purchase.product_variant.product_id,
            name=purchase.product_variant.name,
            description=purchase.product_variant.description,
            price=purchase.product_variant.price,
            enabled=purchase.product_variant.enabled,
            unique=purchase.product_variant.unique,
            school_type=purchase.product_variant.school_type,
            public_type=purchase.product_variant.public_type,
        ),
    )


def volunteer_shift_model_to_schema(
    shift: models_sport_competition.VolunteerShift,
) -> schemas_sport_competition.VolunteerShiftCompleteWithVolunteers:
    return schemas_sport_competition.VolunteerShiftCompleteWithVolunteers(
        id=shift.id,
        edition_id=shift.edition_id,
        name=shift.name,
        manager_id=shift.manager_id,
        description=shift.description,
        value=shift.value,
        start_time=shift.start_time,
        end_time=shift.end_time,
        max_volunteers=shift.max_volunteers,
        location=shift.location,
        registrations=[
            schemas_sport_competition.VolunteerRegistrationWithUser(
                user_id=registration.user_id,
                shift_id=registration.shift_id,
                edition_id=registration.edition_id,
                validated=registration.validated,
                registered_at=registration.registered_at,
                user=schemas_users.CoreUser(
                    email=registration.user.email,
                    name=registration.user.name,
                    school_id=registration.user.school_id,
                    firstname=registration.user.firstname,
                    nickname=registration.user.nickname,
                    account_type=registration.user.account_type,
                    id=registration.user.id,
                ),
            )
            for registration in shift.registrations
        ],
        manager=schemas_users.CoreUser(
            email=shift.manager.email,
            name=shift.manager.name,
            school_id=shift.manager.school_id,
            firstname=shift.manager.firstname,
            nickname=shift.manager.nickname,
            account_type=shift.manager.account_type,
            id=shift.manager.id,
        ),
    )

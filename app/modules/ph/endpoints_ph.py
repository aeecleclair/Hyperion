import uuid
from datetime import UTC, datetime, time, timedelta

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.schemas_notification import Message, Topic
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    get_scheduler,
    is_user_a_member,
    is_user_in,
)
from app.modules.ph import cruds_ph, models_ph, schemas_ph
from app.modules.ph.user_deleter_ph import PHUserDeleter
from app.types.content_type import ContentType
from app.types.module import Module
from app.types.scheduler import Scheduler
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    save_file_as_data,
    save_pdf_first_page_as_image,
)

root = "ph"
ph_topic = Topic(
    id=uuid.UUID("b493c745-adb3-4822-9d1d-1fc6d5152681"),
    module_root=root,
    name="📗 PH",
    topic_identifier=None,
    restrict_to_group_id=None,
    restrict_to_members=True,
)
module = Module(
    root=root,
    tag="ph",
    default_allowed_account_types=[AccountType.student],
    registred_topics=[ph_topic],
    factory=None,
    user_deleter=PHUserDeleter(),
)


@module.router.get(
    "/ph/{paper_id}/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def get_paper_pdf(
    paper_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/pdf/default_ph.pdf",
        directory="ph/pdf",
        filename=str(paper_id),
    )


@module.router.get(
    "/ph/",
    response_model=list[schemas_ph.PaperComplete],
    status_code=200,
)
async def get_papers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return all editions until now, sorted from the latest to the oldest
    """
    return await cruds_ph.get_papers(
        db=db,
        end_date=datetime.now(tz=UTC).date(),
    )  # Return papers from the latest to the oldest until now


@module.router.get(
    "/ph/admin",
    response_model=list[schemas_ph.PaperComplete],
    status_code=200,
)
async def get_papers_admin(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.ph)),
):
    """
    Return all editions, sorted from the latest to the oldest
    """
    return await cruds_ph.get_papers(
        db=db,
    )  # Return all papers from the latest to the oldest


@module.router.post(
    "/ph/",
    response_model=schemas_ph.PaperComplete,
    status_code=201,
)
async def create_paper(
    paper: schemas_ph.PaperBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.ph)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """Create a new paper."""

    paper_complete = schemas_ph.PaperComplete(
        id=uuid.uuid4(),
        **paper.model_dump(),
    )

    paper_db = models_ph.Paper(
        id=paper_complete.id,
        name=paper_complete.name,
        release_date=paper_complete.release_date,
    )

    now = datetime.now(UTC)

    # We only want to send a notification if the paper was released less than a month ago.
    if paper_db.release_date >= now.date() - timedelta(days=30):
        message = Message(
            title=f"📗 PH - {paper_db.name}",
            content="Un nouveau journal est disponible! 🎉",
            action_module="ph",
        )
        if paper_db.release_date == now.date():
            await notification_tool.send_notification_to_topic(
                topic_id=ph_topic.id,
                message=message,
            )
        else:
            delivery_time = time(11, 00, 00, tzinfo=UTC)
            release_date = datetime.combine(paper_db.release_date, delivery_time)
            await notification_tool.send_notification_to_topic(
                topic_id=ph_topic.id,
                message=message,
                scheduler=scheduler,
                defer_date=release_date,
                job_id=f"ph_{paper_db.id}",
            )
    return await cruds_ph.create_paper(paper=paper_db, db=db)


@module.router.post(
    "/ph/{paper_id}/pdf",
    status_code=201,
)
async def create_paper_pdf_and_cover(
    paper_id: uuid.UUID,
    pdf: UploadFile = File(...),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.ph)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    await save_file_as_data(
        upload_file=pdf,
        directory="ph/pdf",
        filename=str(paper_id),
        max_file_size=10 * 1024 * 1024,  # 10 MB
        accepted_content_types=[ContentType.pdf],
    )

    await save_pdf_first_page_as_image(
        input_pdf_directory="ph/pdf",
        output_image_directory="ph/cover",
        filename=str(paper_id),
        default_pdf_path="assets/pdf/default_ph.pdf",
        jpg_quality=95,
    )


@module.router.get(
    "/ph/{paper_id}/cover",
    status_code=200,
)
async def get_cover(
    paper_id: uuid.UUID,
    user: models_users.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/images/default_cover.jpeg",
        directory="ph/cover",
        filename=str(paper_id),
    )


@module.router.patch(
    "/ph/{paper_id}",
    status_code=204,
)
async def update_paper(
    paper_id: uuid.UUID,
    paper_update: schemas_ph.PaperUpdate,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    await cruds_ph.update_paper(
        paper_id=paper_id,
        paper_update=paper_update,
        db=db,
    )


@module.router.delete(
    "/ph/{paper_id}",
    status_code=204,
)
async def delete_paper(
    paper_id: uuid.UUID,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    delete_file_from_data(
        directory="ph/pdf",
        filename=str(paper_id),
    )

    delete_file_from_data(
        directory="ph/cover",
        filename=str(paper_id),
    )

    await cruds_ph.delete_paper(
        paper_id=paper_id,
        db=db,
    )

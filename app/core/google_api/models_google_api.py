from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from app.types.sqlalchemy import Base


class OAuthFlowState(MappedAsDataclass, Base):
    __tablename__ = "google_api_oauth_flow_state"

    state: Mapped[str] = mapped_column(primary_key=True)

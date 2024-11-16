from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class OAuthFlowState(Base):
    __tablename__ = "google_api_oauth_flow_state"

    state: Mapped[str] = mapped_column(primary_key=True)

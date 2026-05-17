from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlueprintModel(Base):
    """생성된 설계도 결과를 저장하기 위한 초기 ORM 모델입니다."""

    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    idea: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

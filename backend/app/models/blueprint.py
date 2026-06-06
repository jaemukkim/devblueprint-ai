from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlueprintModel(Base):
    """생성된 설계도 결과를 저장하기 위한 ORM 모델입니다."""

    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    cache_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    idea: Mapped[str] = mapped_column(Text, nullable=False)
    revision_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BlueprintRunEventModel(Base):
    """설계도 생성 그래프의 노드 실행 이력을 저장하는 ORM 모델입니다."""

    __tablename__ = "blueprint_run_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    blueprint_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_type: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_name: Mapped[str] = mapped_column(Text, nullable=False)
    phase: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    route: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

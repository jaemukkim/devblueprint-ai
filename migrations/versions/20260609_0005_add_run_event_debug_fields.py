"""실행 이력에 specialist와 오류 메시지를 추가합니다."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260609_0005"
down_revision = "20260606_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """blueprint_run_events에 디버깅용 상세 필드를 추가합니다."""
    op.add_column("blueprint_run_events", sa.Column("specialist_id", sa.Text(), nullable=True))
    op.add_column(
        "blueprint_run_events",
        sa.Column(
            "error_messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("blueprint_run_events", "error_messages", server_default=None)


def downgrade() -> None:
    """blueprint_run_events의 디버깅용 상세 필드를 제거합니다."""
    op.drop_column("blueprint_run_events", "error_messages")
    op.drop_column("blueprint_run_events", "specialist_id")

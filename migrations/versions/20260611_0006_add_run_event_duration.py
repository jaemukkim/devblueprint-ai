"""실행 이력에 노드 소요 시간을 추가합니다."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision = "20260611_0006"
down_revision = "20260609_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """blueprint_run_events에 노드별 실행 소요 시간을 저장하는 컬럼을 추가합니다."""
    op.add_column("blueprint_run_events", sa.Column("duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    """blueprint_run_events의 노드별 실행 소요 시간 컬럼을 제거합니다."""
    op.drop_column("blueprint_run_events", "duration_ms")

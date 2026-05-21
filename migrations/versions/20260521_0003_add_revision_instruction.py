"""수정 요청 원문 저장 컬럼 추가

Revision ID: 20260521_0003
Revises: 20260518_0002
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0003"
down_revision: Union[str, None] = "20260518_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """수정본 카드 요약에 사용할 수정 요청 원문 컬럼을 추가합니다."""
    op.add_column("blueprints", sa.Column("revision_instruction", sa.Text(), nullable=True))


def downgrade() -> None:
    """롤백 시 수정 요청 원문 컬럼을 제거합니다."""
    op.drop_column("blueprints", "revision_instruction")

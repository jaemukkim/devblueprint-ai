"""create blueprint run events table

Revision ID: 20260606_0004
Revises: 20260521_0003
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260606_0004"
down_revision: Union[str, None] = "20260521_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """LangGraph 노드 실행 이력을 저장할 테이블을 생성합니다."""
    op.create_table(
        "blueprint_run_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("blueprint_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("run_type", sa.Text(), nullable=False),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("node_name", sa.Text(), nullable=False),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route", sa.Text(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blueprint_run_events_blueprint_id", "blueprint_run_events", ["blueprint_id"])


def downgrade() -> None:
    """LangGraph 노드 실행 이력 테이블을 제거합니다."""
    op.drop_index("ix_blueprint_run_events_blueprint_id", table_name="blueprint_run_events")
    op.drop_table("blueprint_run_events")

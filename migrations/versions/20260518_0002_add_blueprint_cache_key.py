"""add blueprint cache key

Revision ID: 20260518_0002
Revises: 20260518_0001
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260518_0002"
down_revision: Union[str, None] = "20260518_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("blueprints", sa.Column("cache_key", sa.Text(), nullable=True))
    op.execute("UPDATE blueprints SET cache_key = 'legacy:' || id::text WHERE cache_key IS NULL")
    op.alter_column("blueprints", "cache_key", nullable=False)
    op.create_index("ix_blueprints_cache_key", "blueprints", ["cache_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_blueprints_cache_key", table_name="blueprints")
    op.drop_column("blueprints", "cache_key")

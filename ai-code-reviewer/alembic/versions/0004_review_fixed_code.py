"""review fixed code

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reviews", sa.Column("fixed_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reviews", "fixed_code")

"""github login

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_id", sa.String(32), nullable=True))
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Акаунти без пароля (створені через GitHub) не можна зберегти з NOT NULL
    op.execute("DELETE FROM users WHERE hashed_password IS NULL")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_users_github_id", table_name="users")
    op.drop_column("users", "github_id")

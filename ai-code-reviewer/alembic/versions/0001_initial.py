"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("language", sa.String(50), nullable=False, server_default="python"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("language", sa.String(50), nullable=False, server_default="python"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "DONE", "FAILED", name="reviewstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_reviews_project_id", "reviews", ["project_id"])

    op.create_table(
        "review_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column(
            "category",
            sa.Enum("BUG", "SECURITY", "STYLE", "PERFORMANCE", name="commentcategory"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "WARNING", "INFO", name="commentseverity"),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
    )
    op.create_index("ix_review_comments_review_id", "review_comments", ["review_id"])

    # Фрагменти документації для RAG (language IS NULL означає "для всіх мов")
    op.execute(f"""
        CREATE TABLE doc_chunks (
            id SERIAL PRIMARY KEY,
            source VARCHAR(100) NOT NULL,
            language VARCHAR(50),
            content TEXT NOT NULL,
            embedding vector({EMBEDDING_DIM}) NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_doc_chunks_language ON doc_chunks (language)")
    op.execute(
        "CREATE INDEX ix_doc_chunks_embedding ON doc_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS doc_chunks")
    op.drop_table("review_comments")
    op.drop_table("reviews")
    op.drop_table("projects")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS commentseverity")
    op.execute("DROP TYPE IF EXISTS commentcategory")
    op.execute("DROP TYPE IF EXISTS reviewstatus")

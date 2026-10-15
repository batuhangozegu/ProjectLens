"""Create projects and analysis snapshots.

Revision ID: 0001_project_snapshots
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_project_snapshots"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("canonical_repository_url", sa.String(length=2048), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("slug", name=op.f("uq_projects_slug")),
    )
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("analyzer_schema_version", sa.String(length=32), nullable=False),
        sa.Column("partial", sa.Boolean(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("python_file_count", sa.Integer(), nullable=False),
        sa.Column("python_loc", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("cycle_group_count", sa.Integer(), nullable=False),
        sa.Column("diagnostic_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('completed', 'partial', 'failed')", name=op.f("ck_analysis_snapshots_snapshot_status_valid")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_analysis_snapshots_project_id_projects"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_snapshots")),
        sa.UniqueConstraint("project_id", "commit_sha", "analyzer_schema_version", name="uq_snapshot_identity"),
    )
    op.create_index("ix_snapshot_project_created", "analysis_snapshots", ["project_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_snapshot_project_created", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
    op.drop_table("projects")

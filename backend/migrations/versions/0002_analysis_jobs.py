"""Persist API analysis job lifecycle.

Revision ID: 0002_analysis_jobs
Revises: 0001_project_snapshots
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_analysis_jobs"
down_revision = "0001_project_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_project_canonical_repository_url", "projects", ["canonical_repository_url"], unique=True)
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("requested_commit", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=240), nullable=True),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name=op.f("ck_analysis_jobs_job_status_valid")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_analysis_jobs_project_id_projects"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["analysis_snapshots.id"], name=op.f("fk_analysis_jobs_snapshot_id_analysis_snapshots"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_jobs")),
    )
    op.create_index("ix_job_project_status", "analysis_jobs", ["project_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_project_status", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("uq_project_canonical_repository_url", table_name="projects")

"""Persist task file links and acceptance criteria."""
from alembic import op
import sqlalchemy as sa

revision = "0004_task_links_and_criteria"
down_revision = "0003_project_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_file_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("length(path) BETWEEN 1 AND 500", name=op.f("ck_task_file_links_task_file_link_path_length")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_task_file_links_task_id_tasks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_file_links")),
        sa.UniqueConstraint("task_id", "path", name="uq_task_file_link_task_path"),
    )
    op.create_index("ix_task_file_links_task_id", "task_file_links", ["task_id"])

    op.create_table(
        "acceptance_criteria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=False),
        sa.Column("attested", sa.Boolean(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("kind IN ('file_exists', 'path_has_files', 'import_edge_exists', 'not_in_cycle', 'max_todo_markers', 'no_analysis_failures', 'manual_attestation')", name=op.f("ck_acceptance_criteria_acceptance_criterion_kind_valid")),
        sa.CheckConstraint("length(description) <= 500", name=op.f("ck_acceptance_criteria_acceptance_criterion_description_length")),
        sa.CheckConstraint("kind = 'manual_attestation' OR attested IS NULL", name=op.f("ck_acceptance_criteria_acceptance_criterion_attested_kind")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_acceptance_criteria_acceptance_criterion_position_nonnegative")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_acceptance_criteria_task_id_tasks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acceptance_criteria")),
    )
    op.create_index("ix_acceptance_criteria_task_id", "acceptance_criteria", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_acceptance_criteria_task_id", table_name="acceptance_criteria")
    op.drop_table("acceptance_criteria")
    op.drop_index("ix_task_file_links_task_id", table_name="task_file_links")
    op.drop_table("task_file_links")

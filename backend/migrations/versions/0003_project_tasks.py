"""Add project-scoped tasks. Revision 0003_project_tasks; revises 0002_analysis_jobs."""
from alembic import op
import sqlalchemy as sa

revision = "0003_project_tasks"
down_revision = "0002_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(4000), nullable=True),
        sa.Column("status", sa.String(16), server_default="TODO", nullable=False),
        sa.Column("priority", sa.String(16), server_default="MEDIUM", nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), server_default="manual", nullable=False),
        sa.Column("source_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 200", name=op.f("ck_tasks_task_title_length")),
        sa.CheckConstraint("description IS NULL OR length(description) <= 4000", name=op.f("ck_tasks_task_description_length")),
        sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED')", name=op.f("ck_tasks_task_status_valid")),
        sa.CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name=op.f("ck_tasks_task_priority_valid")),
        sa.CheckConstraint("source IN ('manual', 'import')", name=op.f("ck_tasks_task_source_valid")),
        sa.CheckConstraint("category IS NULL OR (length(category) BETWEEN 1 AND 80 AND category = trim(category))", name=op.f("ck_tasks_task_category_valid")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_tasks_task_position_nonnegative")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_tasks_project_id_projects"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.UniqueConstraint("project_id", "source_key", name="uq_task_project_source_key"),
    )
    op.create_index("ix_tasks_project_status", "tasks", ["project_id", "status"])
    op.create_index("ix_tasks_project_priority", "tasks", ["project_id", "priority"])


def downgrade() -> None:
    op.drop_index("ix_tasks_project_priority", table_name="tasks")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
    op.drop_table("tasks")

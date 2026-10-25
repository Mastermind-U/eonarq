from alembic import op
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    Uuid,
)

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        Column("id", Uuid, primary_key=True),
        Column("parent_id", Uuid, nullable=True),
        Column("kind", String(7), nullable=False),
        Column("title", String(200), nullable=False),
        Column("prompt", Text, nullable=False),
        Column("status", String(11), nullable=False),
        Column("position", Integer, nullable=False),
        Column("version", Integer, nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("updated_at", DateTime, nullable=False),
        ForeignKeyConstraint(
            ["parent_id"],
            ["tasks.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "kind IN ('epic','master','subtask')",
            name="task_kind",
        ),
        CheckConstraint(
            "status IN ('todo','in_progress','blocked','done')",
            name="task_status",
        ),
        CheckConstraint(
            "(kind='epic' AND parent_id IS NULL) OR "
            "(kind!='epic' AND parent_id IS NOT NULL)",
            name="task_root",
        ),
        CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 200",
            name="task_title",
        ),
        CheckConstraint("length(prompt) <= 200000", name="task_prompt"),
        CheckConstraint(
            "position BETWEEN 0 AND 1000000 AND version >= 1",
            name="task_version_position",
        ),
    )
    op.create_index(
        "ix_tasks_parent_position",
        "tasks",
        ["parent_id", "position", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_parent_position", table_name="tasks")
    op.drop_table("tasks")

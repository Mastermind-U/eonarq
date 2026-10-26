from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)
from eonarq.shared_kernel.infrastructure.database import metadata


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        _dialect: Dialect,
    ) -> datetime | None:
        return value.astimezone(UTC).replace(tzinfo=None) if value else None

    def process_result_value(
        self,
        value: datetime | None,
        _dialect: Dialect,
    ) -> datetime | None:
        return value.replace(tzinfo=UTC) if value else None


def enum_values(enum_type: Any) -> list[str]:
    return [item.value for item in enum_type]


projects_t = Table(
    "projects",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("version", Integer, nullable=False),
    CheckConstraint(
        "length(trim(title)) BETWEEN 1 AND 200",
        name="project_title",
    ),
    CheckConstraint("length(prompt) <= 200000", name="project_prompt"),
    CheckConstraint("version >= 1", name="project_version"),
)

tasks_t = Table(
    "tasks",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("project_id", Uuid, ForeignKey("projects.id"), nullable=False),
    Column(
        "parent_id",
        Uuid,
        nullable=True,
    ),
    Column(
        "kind",
        Enum(TaskKind, values_callable=enum_values, native_enum=False),
        nullable=False,
    ),
    Column("title", String(200), nullable=False),
    Column("prompt", Text, nullable=False),
    Column(
        "action",
        Enum(TaskAction, values_callable=enum_values, native_enum=False),
        nullable=False,
    ),
    Column(
        "status",
        Enum(TaskStatus, values_callable=enum_values, native_enum=False),
        nullable=False,
    ),
    Column("position", Integer, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("updated_at", UTCDateTime, nullable=False),
    CheckConstraint("kind IN ('epic','master','subtask')", name="task_kind"),
    CheckConstraint(
        "status IN ('todo','in_progress','blocked','done','cancelled')",
        name="task_status",
    ),
    CheckConstraint(
        "action IN ('RESEARCH','ACTION','CHECK')",
        name="task_action",
    ),
    UniqueConstraint("project_id", "id", name="task_project_identity"),
    ForeignKeyConstraint(
        ["project_id", "parent_id"],
        ["tasks.project_id", "tasks.id"],
        deferrable=True,
        initially="DEFERRED",
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
Index(
    "ix_tasks_parent_position",
    tasks_t.c.parent_id,
    tasks_t.c.position,
    tasks_t.c.id,
)
Index("ix_tasks_project_status", tasks_t.c.project_id, tasks_t.c.status)

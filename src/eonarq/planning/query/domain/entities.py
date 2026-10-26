from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)
from eonarq.shared_kernel.domain.entities import BaseEntity


@dataclass(slots=True)
class TaskRecord(BaseEntity):
    id: UUID
    title: str
    kind: TaskKind
    parent_id: UUID | None
    prompt: str
    status: TaskStatus
    position: int
    version: int
    created_at: datetime
    updated_at: datetime
    project_id: UUID
    action: TaskAction
    report: str


@dataclass(slots=True)
class ProjectRecord(BaseEntity):
    id: UUID
    title: str
    prompt: str
    version: int

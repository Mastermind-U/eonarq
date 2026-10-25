from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from eonarq.planning.common.domain.types import TaskKind, TaskStatus
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

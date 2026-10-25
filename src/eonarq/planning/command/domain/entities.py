from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid7

from eonarq.planning.common.domain.exceptions import TaskConflict
from eonarq.planning.common.domain.invariants import (
    ensure_position,
    ensure_status,
    ensure_text,
)
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from eonarq.shared_kernel.domain.entities import BaseEntity


@dataclass(slots=True)
class Task(BaseEntity):
    title: str
    kind: TaskKind
    parent_id: UUID | None = None
    prompt: str = ""
    status: TaskStatus = TaskStatus.TODO
    position: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid7)

    def __post_init__(self) -> None:
        """Validate construction before the object is used."""
        ensure_text(self.title, self.prompt)
        ensure_position(self.position)
        ensure_status(self.status)
        self.title = self.title.strip()

    def ensure_version(self, expected: int) -> None:
        if self.version != expected:
            raise TaskConflict(
                "Task changed since it was loaded; reload before editing",
            )

    def touch(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(UTC)

    def reopen(self) -> None:
        if self.status == TaskStatus.DONE:
            self.status = TaskStatus.IN_PROGRESS
            self.touch()

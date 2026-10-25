from dataclasses import dataclass
from uuid import UUID

from eonarq.planning.common.domain.types import TaskKind, TaskStatus


@dataclass(frozen=True, slots=True)
class CreateTaskInput:
    title: str
    kind: TaskKind
    parent_id: UUID | None = None
    prompt: str = ""
    position: int = 0


@dataclass(frozen=True, slots=True)
class UpdateTaskInput:
    task_id: UUID
    expected_version: int
    title: str | None = None
    prompt: str | None = None
    status: TaskStatus | None = None
    position: int | None = None


@dataclass(frozen=True, slots=True)
class MoveTaskInput:
    task_id: UUID
    parent_id: UUID
    expected_version: int


@dataclass(frozen=True, slots=True)
class DeleteTaskInput:
    task_id: UUID
    expected_version: int
    recursive: bool = False


@dataclass(frozen=True, slots=True)
class MutationOutput:
    task_id: UUID
    version: int

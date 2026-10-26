from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)


@dataclass(frozen=True, slots=True)
class BoardInput:
    epic_id: UUID | None = None
    project_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class TaskInput:
    task_id: UUID


@dataclass(frozen=True, slots=True)
class FlowMetricsData:
    total: int
    todo: int
    in_progress: int
    blocked: int
    done: int
    wip: int
    completion_percent: float
    cancelled: int


@dataclass(frozen=True, slots=True)
class TaskData:
    id: UUID
    parent_id: UUID | None
    kind: TaskKind
    title: str
    status: TaskStatus
    position: int
    version: int
    done: int
    total: int
    percent: float
    flow: FlowMetricsData
    project_id: UUID
    action: TaskAction


@dataclass(frozen=True, slots=True)
class CellData:
    id: UUID
    epic_id: UUID
    master_id: UUID | None
    title: str
    status: TaskStatus


@dataclass(frozen=True, slots=True)
class BoardOutput:
    tasks: tuple[TaskData, ...]
    cells: tuple[CellData, ...]
    done: int
    total: int
    percent: float
    flow: FlowMetricsData


@dataclass(frozen=True, slots=True)
class TaskOutput:
    id: UUID
    parent_id: UUID | None
    kind: TaskKind
    title: str
    prompt: str
    status: TaskStatus
    position: int
    version: int
    created_at: datetime
    updated_at: datetime
    project_id: UUID
    action: TaskAction
    report: str


@dataclass(frozen=True, slots=True)
class ProjectData:
    id: UUID
    title: str
    prompt: str
    version: int


@dataclass(frozen=True, slots=True)
class ProjectsInput:
    pass


@dataclass(frozen=True, slots=True)
class PromptOutput:
    task_id: UUID
    title: str
    content: str

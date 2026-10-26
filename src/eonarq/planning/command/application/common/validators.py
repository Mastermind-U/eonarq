from uuid import UUID

from eonarq.planning.command.application.dtos import (
    CreateProjectInput,
    CreateTaskInput,
    DeleteTaskInput,
    MoveTaskInput,
    UpdateProjectInput,
    UpdateTaskInput,
)
from eonarq.planning.common.domain.exceptions import InvalidTask
from eonarq.planning.common.domain.invariants import (
    ensure_action,
    ensure_position,
    ensure_status,
    ensure_text,
)
from eonarq.planning.common.domain.types import TaskKind


def validate_create(data: CreateTaskInput) -> None:
    ensure_text(data.title, data.prompt)
    ensure_position(data.position)
    ensure_action(data.action)
    if data.project_id is not None and not isinstance(data.project_id, UUID):
        raise InvalidTask("Project ID must be a UUID")
    if not isinstance(data.kind, TaskKind):
        raise InvalidTask("Unknown task kind")
    if data.parent_id is not None and not isinstance(data.parent_id, UUID):
        raise InvalidTask("Parent ID must be a UUID")


def validate_update(data: UpdateTaskInput) -> None:
    validate_version(data.task_id, data.expected_version)
    if data.action is not None:
        ensure_action(data.action)
    if data.title is not None:
        ensure_text(data.title, "")
    if data.prompt is not None:
        ensure_text("Task", data.prompt)
    if data.status is not None:
        ensure_status(data.status)
    if data.position is not None:
        ensure_position(data.position)


def validate_move(data: MoveTaskInput) -> None:
    validate_version(data.task_id, data.expected_version)
    if not isinstance(data.parent_id, UUID):
        raise InvalidTask("Parent ID must be a UUID")


def validate_delete(data: DeleteTaskInput) -> None:
    validate_version(data.task_id, data.expected_version)
    if type(data.recursive) is not bool:
        raise InvalidTask("Recursive must be a boolean")


def validate_version(task_id: UUID, version: int) -> None:
    if not isinstance(task_id, UUID):
        raise InvalidTask("Task ID must be a UUID")
    if type(version) is not int or version < 1:
        raise InvalidTask("Expected version must be a positive integer")


def validate_project_id(project_id: UUID) -> None:
    if not isinstance(project_id, UUID):
        raise InvalidTask("Project ID must be a UUID")


def validate_create_project(data: CreateProjectInput) -> None:
    ensure_text(data.title, data.prompt)


def validate_update_project(data: UpdateProjectInput) -> None:
    validate_version(data.project_id, data.expected_version)
    if data.title is not None:
        ensure_text(data.title, "")
    if data.prompt is not None:
        ensure_text("Project", data.prompt)

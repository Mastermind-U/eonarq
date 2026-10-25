from uuid import UUID

from eonarq.planning.common.domain.exceptions import InvalidTask


def validate_id(task_id: UUID | None, *, optional: bool = False) -> None:
    if optional and task_id is None:
        return
    if not isinstance(task_id, UUID):
        raise InvalidTask("Task ID must be a UUID")

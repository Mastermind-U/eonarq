from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.types import TaskStatus


def reopen_ancestors(
    task: Task,
    repository: TaskRepository,
    *,
    cancelled_ancestors_only: bool = False,
) -> None:
    parent_id = task.parent_id
    while parent_id is not None:
        parent = repository.load(parent_id)
        if (
            not cancelled_ancestors_only
            or parent.status == TaskStatus.CANCELLED
        ):
            parent.reopen()
            cancelled_ancestors_only = False
        parent_id = parent.parent_id

from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Task


def reopen_ancestors(task: Task, repository: TaskRepository) -> None:
    parent_id = task.parent_id
    while parent_id is not None:
        parent = repository.load(parent_id)
        parent.reopen()
        parent_id = parent.parent_id

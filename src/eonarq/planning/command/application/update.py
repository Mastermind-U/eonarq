from dataclasses import dataclass

from eonarq.planning.command.application.common.hierarchy import (
    reopen_ancestors,
)
from eonarq.planning.command.application.common.validators import (
    validate_update,
)
from eonarq.planning.command.application.dtos import (
    MutationOutput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.common.domain.exceptions import TaskConflict
from eonarq.planning.common.domain.types import TaskStatus
from eonarq.shared_kernel.application.gateways import TransactionManager


@dataclass(slots=True)
class UpdateTask:
    repository: TaskRepository
    transaction: TransactionManager

    def execute(self, data: UpdateTaskInput) -> MutationOutput:
        validate_update(data)
        try:
            self.transaction.begin()
            task = self.repository.load(data.task_id)
            task.ensure_version(data.expected_version)
            if data.status == TaskStatus.DONE and any(
                child.status != TaskStatus.DONE
                for child in self.repository.load_children(task.id)
            ):
                raise TaskConflict(
                    "Complete every child before closing this task",
                )
            if data.title is not None:
                task.title = data.title.strip()
            if data.prompt is not None:
                task.prompt = data.prompt
            if data.position is not None:
                task.position = data.position
            if data.status is not None:
                task.status = data.status
            task.touch()
            if task.status != TaskStatus.DONE:
                reopen_ancestors(task, self.repository)
            self.transaction.commit()
            return MutationOutput(task.id, task.version)
        except BaseException:
            self.transaction.rollback()
            raise

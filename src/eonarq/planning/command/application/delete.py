from dataclasses import dataclass

from eonarq.planning.command.application.common.validators import (
    validate_delete,
)
from eonarq.planning.command.application.dtos import (
    DeleteTaskInput,
    MutationOutput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import TaskConflict
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)


@dataclass(slots=True)
class DeleteTask:
    repository: TaskRepository
    saver: EntitySaver
    transaction: TransactionManager

    def execute(self, data: DeleteTaskInput) -> MutationOutput:
        validate_delete(data)
        try:
            self.transaction.begin()
            task = self.repository.load(data.task_id)
            task.ensure_version(data.expected_version)
            if self.repository.load_children(task.id) and not data.recursive:
                raise TaskConflict(
                    "Task has children; explicitly choose recursive deletion",
                )
            if task.parent_id:
                self.repository.load(task.parent_id).touch()
            self._delete_tree(task)
            self.transaction.commit()
            return MutationOutput(task.id, task.version)
        except BaseException:
            self.transaction.rollback()
            raise

    def _delete_tree(self, task: Task) -> None:
        for child in self.repository.load_children(task.id):
            self._delete_tree(child)
        self.saver.delete(task)

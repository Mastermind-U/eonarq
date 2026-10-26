from dataclasses import dataclass

from eonarq.planning.command.application.common.validators import (
    validate_project_id,
)
from eonarq.planning.command.application.dtos import (
    ClearCancelledInput,
    ClearCancelledOutput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.common.domain.exceptions import TaskConflict
from eonarq.planning.common.domain.types import TaskStatus
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)


@dataclass(slots=True)
class ClearCancelled:
    repository: TaskRepository
    saver: EntitySaver
    transaction: TransactionManager

    def execute(self, data: ClearCancelledInput) -> ClearCancelledOutput:
        validate_project_id(data.project_id)
        try:
            self.transaction.begin()
            self.repository.load_project(data.project_id)
            tasks = self.repository.load_project_tasks(data.project_id)
            cancelled = {
                task.id
                for task in tasks
                if task.status == TaskStatus.CANCELLED
            }
            if any(
                task.parent_id in cancelled and task.id not in cancelled
                for task in tasks
            ):
                raise TaskConflict(
                    "Cancelled branches must not contain active tasks",
                )
            parents = {
                task.parent_id
                for task in tasks
                if task.id in cancelled and task.parent_id is not None
            } - cancelled
            for parent_id in parents:
                self.repository.load(parent_id).touch()
            for task in tasks:
                if task.id in cancelled:
                    self.saver.delete(task)
            self.transaction.commit()
            return ClearCancelledOutput(len(cancelled))
        except BaseException:
            self.transaction.rollback()
            raise

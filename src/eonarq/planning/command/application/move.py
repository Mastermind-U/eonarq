from dataclasses import dataclass

from eonarq.planning.command.application.common.hierarchy import (
    reopen_ancestors,
)
from eonarq.planning.command.application.common.validators import validate_move
from eonarq.planning.command.application.dtos import (
    MoveTaskInput,
    MutationOutput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.common.domain.exceptions import InvalidTask
from eonarq.planning.common.domain.invariants import ensure_parent
from eonarq.planning.common.domain.types import TaskStatus
from eonarq.shared_kernel.application.gateways import TransactionManager


@dataclass(slots=True)
class MoveTask:
    repository: TaskRepository
    transaction: TransactionManager

    def execute(self, data: MoveTaskInput) -> MutationOutput:
        validate_move(data)
        try:
            self.transaction.begin()
            task = self.repository.load(data.task_id)
            task.ensure_version(data.expected_version)
            old_parent_id = task.parent_id
            if old_parent_id is None:
                raise InvalidTask("Hierarchy does not allow moving an epic")
            parent = self.repository.load(data.parent_id)
            ensure_parent(task.kind, parent.kind)
            if task.project_id != parent.project_id:
                raise InvalidTask(
                    "Moving tasks across projects is not allowed",
                )
            if task.parent_id != parent.id:
                self.repository.load(old_parent_id).touch()
                task.parent_id = parent.id
                parent.touch()
                if (
                    parent.status == TaskStatus.CANCELLED
                    or task.status
                    not in (
                        TaskStatus.DONE,
                        TaskStatus.CANCELLED,
                    )
                ):
                    parent.reopen()
                    reopen_ancestors(parent, self.repository)
            task.touch()
            self.transaction.commit()
            return MutationOutput(task.id, task.version)
        except BaseException:
            self.transaction.rollback()
            raise

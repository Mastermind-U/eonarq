from dataclasses import dataclass

from eonarq.planning.command.application.common.hierarchy import (
    reopen_ancestors,
)
from eonarq.planning.command.application.common.validators import (
    validate_create,
)
from eonarq.planning.command.application.dtos import (
    CreateTaskInput,
    MutationOutput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.invariants import ensure_parent
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)


@dataclass(slots=True)
class CreateTask:
    repository: TaskRepository
    saver: EntitySaver
    transaction: TransactionManager

    def execute(self, data: CreateTaskInput) -> MutationOutput:
        validate_create(data)
        try:
            self.transaction.begin()
            parent = (
                self.repository.load(data.parent_id)
                if data.parent_id
                else None
            )
            ensure_parent(data.kind, parent.kind if parent else None)
            task = Task(
                title=data.title,
                kind=data.kind,
                parent_id=data.parent_id,
                prompt=data.prompt,
                position=data.position,
            )
            self.saver.add(task)
            if parent:
                parent.touch()
                parent.reopen()
                reopen_ancestors(parent, self.repository)
            self.transaction.commit()
            return MutationOutput(task.id, task.version)
        except BaseException:
            self.transaction.rollback()
            raise

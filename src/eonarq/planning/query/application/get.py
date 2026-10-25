from dataclasses import dataclass

from eonarq.planning.query.application.common.validators import validate_id
from eonarq.planning.query.application.dtos import TaskInput, TaskOutput
from eonarq.planning.query.application.gateways import TaskReader


@dataclass(slots=True)
class GetTask:
    reader: TaskReader

    def execute(self, data: TaskInput) -> TaskOutput:
        validate_id(data.task_id)
        task = self.reader.load(data.task_id)
        return TaskOutput(
            task.id,
            task.parent_id,
            task.kind,
            task.title,
            task.prompt,
            task.status,
            task.position,
            task.version,
            task.created_at,
            task.updated_at,
        )

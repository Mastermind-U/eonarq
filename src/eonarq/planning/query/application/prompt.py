from dataclasses import dataclass

from eonarq.planning.query.application.common.validators import validate_id
from eonarq.planning.query.application.dtos import PromptOutput, TaskInput
from eonarq.planning.query.application.gateways import TaskReader


@dataclass(slots=True)
class GetTaskPrompt:
    reader: TaskReader

    def execute(self, data: TaskInput) -> PromptOutput:
        validate_id(data.task_id)
        task = self.reader.load(data.task_id)
        chain = [task]
        while chain[-1].parent_id is not None:
            chain.append(self.reader.load(chain[-1].parent_id))
        sections = [
            f"# {item.kind.value.title()}: {item.title}\n\n{item.prompt}"
            for item in reversed(chain)
        ]
        content = "\n\n---\n\n".join(sections)
        content += (
            f"\n\nTask ID: {task.id}\nVersion: {task.version}\n"
            f"Status: {task.status.value}\n"
        )
        return PromptOutput(task.id, task.title, content)

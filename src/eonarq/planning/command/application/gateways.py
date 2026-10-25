from typing import Protocol
from uuid import UUID

from eonarq.planning.command.domain.entities import Task


class TaskRepository(Protocol):
    def load(self, task_id: UUID) -> Task: ...

    def load_children(self, parent_id: UUID) -> list[Task]: ...

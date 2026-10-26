from typing import Protocol
from uuid import UUID

from eonarq.planning.command.domain.entities import Project, Task


class TaskRepository(Protocol):
    def load(self, task_id: UUID) -> Task: ...

    def load_children(self, parent_id: UUID) -> list[Task]: ...

    def load_project(self, project_id: UUID) -> Project: ...

    def load_project_tasks(self, project_id: UUID) -> list[Task]: ...

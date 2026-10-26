from typing import Protocol
from uuid import UUID

from eonarq.planning.query.domain.entities import ProjectRecord, TaskRecord


class TaskReader(Protocol):
    def load(self, task_id: UUID) -> TaskRecord: ...

    def load_all(self, project_id: UUID | None = None) -> list[TaskRecord]: ...

    def load_project(self, project_id: UUID) -> ProjectRecord: ...

    def list_projects(self) -> list[ProjectRecord]: ...

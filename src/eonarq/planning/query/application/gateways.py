from typing import Protocol
from uuid import UUID

from eonarq.planning.query.domain.entities import TaskRecord


class TaskReader(Protocol):
    def load(self, task_id: UUID) -> TaskRecord: ...

    def load_all(self) -> list[TaskRecord]: ...

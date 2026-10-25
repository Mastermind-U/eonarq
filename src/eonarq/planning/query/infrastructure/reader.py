from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eonarq.planning.common.domain.exceptions import TaskNotFound
from eonarq.planning.common.infrastructure.tables import tasks_t
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.infrastructure.tables import TaskRecord


class SQLiteTaskReader(TaskReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, task_id: UUID) -> TaskRecord:
        task = self._session.get(TaskRecord, task_id)
        if task is None:
            raise TaskNotFound("Task not found")
        return task

    def load_all(self) -> list[TaskRecord]:
        statement = select(tasks_t).order_by(tasks_t.c.position, tasks_t.c.id)
        return list(
            self._session.scalars(
                select(TaskRecord).from_statement(statement),
            ),
        )

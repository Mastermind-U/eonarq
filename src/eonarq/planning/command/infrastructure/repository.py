from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.infrastructure.tables import Task
from eonarq.planning.common.domain.exceptions import TaskNotFound
from eonarq.planning.common.infrastructure.tables import tasks_t


class SQLiteTaskRepository(TaskRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, task_id: UUID) -> Task:
        task = self._session.get(Task, task_id)
        if task is None:
            raise TaskNotFound("Task not found")
        return task

    def load_children(self, parent_id: UUID) -> list[Task]:
        statement = (
            select(tasks_t)
            .where(tasks_t.c.parent_id == parent_id)
            .order_by(tasks_t.c.position, tasks_t.c.id)
        )
        return list(
            self._session.scalars(select(Task).from_statement(statement)),
        )

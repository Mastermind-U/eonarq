from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eonarq.planning.common.domain.exceptions import TaskNotFound
from eonarq.planning.common.infrastructure.tables import projects_t, tasks_t
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.infrastructure.tables import (
    ProjectRecord,
    TaskRecord,
)


class SQLiteTaskReader(TaskReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, task_id: UUID) -> TaskRecord:
        task = self._session.get(TaskRecord, task_id)
        if task is None:
            raise TaskNotFound("Task not found")
        return task

    def load_all(self, project_id: UUID | None = None) -> list[TaskRecord]:
        statement = select(tasks_t).order_by(tasks_t.c.position, tasks_t.c.id)
        if project_id is not None:
            statement = statement.where(tasks_t.c.project_id == project_id)
        return list(
            self._session.scalars(
                select(TaskRecord).from_statement(statement),
            ),
        )

    def load_project(self, project_id: UUID) -> ProjectRecord:
        project = self._session.get(ProjectRecord, project_id)
        if project is None:
            raise TaskNotFound("Project not found")
        return project

    def list_projects(self) -> list[ProjectRecord]:
        statement = select(projects_t).order_by(
            projects_t.c.title,
            projects_t.c.id,
        )
        return list(
            self._session.scalars(
                select(ProjectRecord).from_statement(statement),
            ),
        )

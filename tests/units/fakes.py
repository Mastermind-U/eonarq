from copy import deepcopy
from dataclasses import fields
from typing import Any
from uuid import UUID

from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Project, Task
from eonarq.planning.common.domain.exceptions import TaskNotFound
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.domain.entities import ProjectRecord, TaskRecord
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)
from eonarq.shared_kernel.domain.entities import BaseEntity


class MemoryStore(TaskRepository, EntitySaver, TransactionManager):
    def __init__(self) -> None:
        self.tasks: dict[UUID, Task] = {}
        self.project = Project("Test project", "Project instructions")
        self.projects = {self.project.id: self.project}
        self._project_snapshot: dict[UUID, tuple[Project, dict[str, Any]]] = {}
        self.commits = 0
        self.rollbacks = 0
        self.begins = 0
        self.commit_error: BaseException | None = None
        self.begin_error: BaseException | None = None
        self._snapshot: dict[UUID, tuple[Task, dict[str, Any]]] = {}

    def begin(self) -> None:
        self.begins += 1
        self._project_snapshot = {
            key: (
                project,
                {
                    field.name: deepcopy(getattr(project, field.name))
                    for field in fields(project)
                },
            )
            for key, project in self.projects.items()
        }
        self._snapshot = {
            key: (
                task,
                {
                    field.name: deepcopy(getattr(task, field.name))
                    for field in fields(task)
                },
            )
            for key, task in self.tasks.items()
        }
        if self.begin_error:
            raise self.begin_error

    def commit(self) -> None:
        if self.commit_error:
            raise self.commit_error
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
        self.projects.clear()
        for key, (project, values) in self._project_snapshot.items():
            for name, value in values.items():
                setattr(project, name, value)
            self.projects[key] = project
        self.tasks.clear()
        for key, (task, values) in self._snapshot.items():
            for name, value in values.items():
                setattr(task, name, value)
            self.tasks[key] = task

    def load(self, task_id: UUID) -> Task:
        if task_id not in self.tasks:
            raise TaskNotFound("Task not found")
        return self.tasks[task_id]

    def load_children(self, parent_id: UUID) -> list[Task]:
        return [
            task for task in self.tasks.values() if task.parent_id == parent_id
        ]

    def add(self, entity: BaseEntity) -> None:
        if isinstance(entity, Project):
            self.projects[entity.id] = entity
            return
        if not isinstance(entity, Task):
            raise TypeError("Expected a Task")
        self.tasks[entity.id] = entity

    def delete(self, entity: BaseEntity) -> None:
        if not isinstance(entity, Task):
            raise TypeError("Expected a Task")
        del self.tasks[entity.id]

    def load_project(self, project_id: UUID) -> Project:
        if project_id not in self.projects:
            raise TaskNotFound("Project not found")
        return self.projects[project_id]

    def load_project_tasks(self, project_id: UUID) -> list[Task]:
        return [
            task
            for task in self.tasks.values()
            if task.project_id == project_id
        ]


class MemoryTaskReader(TaskReader):
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def load(self, task_id: UUID) -> TaskRecord:
        task = self._store.load(task_id)
        return TaskRecord(
            **{
                field.name: getattr(task, field.name) for field in fields(task)
            },
        )

    def load_all(self, project_id: UUID | None = None) -> list[TaskRecord]:
        return [
            self.load(task_id)
            for task_id, task in self._store.tasks.items()
            if project_id is None or task.project_id == project_id
        ]

    def load_project(self, project_id: UUID) -> ProjectRecord:
        project = self._store.load_project(project_id)
        return ProjectRecord(
            project.id,
            project.title,
            project.prompt,
            project.version,
        )

    def list_projects(self) -> list[ProjectRecord]:
        return [
            self.load_project(project_id)
            for project_id in self._store.projects
        ]

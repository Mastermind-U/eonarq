from copy import deepcopy
from dataclasses import fields
from typing import Any
from uuid import UUID

from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import TaskNotFound
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.domain.entities import TaskRecord
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)
from eonarq.shared_kernel.domain.entities import BaseEntity


class MemoryStore(TaskRepository, EntitySaver, TransactionManager):
    def __init__(self) -> None:
        self.tasks: dict[UUID, Task] = {}
        self.commits = 0
        self.rollbacks = 0
        self.begins = 0
        self.commit_error: BaseException | None = None
        self.begin_error: BaseException | None = None
        self._snapshot: dict[UUID, tuple[Task, dict[str, Any]]] = {}

    def begin(self) -> None:
        self.begins += 1
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
        if not isinstance(entity, Task):
            raise TypeError("Expected a Task")
        self.tasks[entity.id] = entity

    def delete(self, entity: BaseEntity) -> None:
        if not isinstance(entity, Task):
            raise TypeError("Expected a Task")
        del self.tasks[entity.id]


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

    def load_all(self) -> list[TaskRecord]:
        return [self.load(task_id) for task_id in self._store.tasks]

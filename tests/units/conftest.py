import pytest

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.dtos import CreateTaskInput
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.types import TaskKind
from tests.units.fakes import MemoryStore


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def tree(store: MemoryStore) -> tuple[Task, Task, Task]:
    create = CreateTask(store, store, store)
    epic = store.load(
        create.execute(
            CreateTaskInput(
                "Epic",
                TaskKind.EPIC,
                prompt="Epic context",
                project_id=store.project.id,
            ),
        ).task_id,
    )
    master = store.load(
        create.execute(
            CreateTaskInput(
                "Master",
                TaskKind.MASTER,
                epic.id,
                "Master context",
            ),
        ).task_id,
    )
    child = store.load(
        create.execute(
            CreateTaskInput(
                "Subtask",
                TaskKind.SUBTASK,
                master.id,
                "Subtask context",
            ),
        ).task_id,
    )
    return epic, master, child

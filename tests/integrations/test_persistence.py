import contextlib
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from dishka import Container
from sqlalchemy import Engine, inspect, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.create_project import CreateProject
from eonarq.planning.command.application.dtos import (
    CreateProjectInput,
    CreateTaskInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import InvalidTask, TaskConflict
from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)
from eonarq.planning.common.infrastructure.tables import tasks_t
from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.dtos import BoardInput, TaskInput
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.application.get import GetTask
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)
from eonarq.shared_kernel.infrastructure.config import Config
from eonarq.shared_kernel.infrastructure.migrations import migrate


def test_action_constraint_uses_validate(container: Container) -> None:
    _, _, child = seed(container)
    with container() as scope:
        scope.get(UpdateTask).execute(
            UpdateTaskInput(child, 1, action=TaskAction.VALIDATE),
        )
    statement = (
        update(tasks_t).where(tasks_t.c.id == child).values(action="CHECK")
    )
    with (
        pytest.raises(IntegrityError),
        container.get(Engine).begin() as connection,
    ):
        connection.execute(statement)
    with container() as scope:
        assert (
            scope.get(GetTask).execute(TaskInput(child)).action
            == TaskAction.VALIDATE
        )


def seed(container: Container) -> tuple[UUID, UUID, UUID]:
    with container() as scope:
        project_id = (
            scope.get(CreateProject)
            .execute(CreateProjectInput("Test project"))
            .project_id
        )
    with container() as scope:
        epic = (
            scope.get(CreateTask)
            .execute(
                CreateTaskInput("Epic", TaskKind.EPIC, project_id=project_id),
            )
            .task_id
        )
    with container() as scope:
        master = (
            scope.get(CreateTask)
            .execute(CreateTaskInput("Master", TaskKind.MASTER, epic))
            .task_id
        )
    with container() as scope:
        child = (
            scope.get(CreateTask)
            .execute(CreateTaskInput("Child", TaskKind.SUBTASK, master))
            .task_id
        )
    return epic, master, child


def test_sqlite_pragmas_and_read_only_query_mapping(
    container: Container,
) -> None:
    epic, _, _ = seed(container)
    with container() as scope:
        session = scope.get(Session)
        assert session.scalar(text("PRAGMA foreign_keys")) == 1
        assert session.scalar(text("PRAGMA read_uncommitted")) == 0
        assert session.scalar(text("PRAGMA journal_mode")) == "wal"
        task = scope.get(TaskReader).load(epic)
        task.title = "Forbidden write"
        with pytest.raises(InvalidTask, match="read-only"):
            session.commit()
        session.rollback()
    with container() as scope:
        assert scope.get(TaskReader).load(epic).title == "Epic"


@pytest.mark.parametrize("action", ["modify", "delete", "invalid_commit"])
def test_rollback_restores_loaded_entities(
    container: Container,
    action: str,
) -> None:
    _, _, child = seed(container)
    with container() as scope:
        transaction = scope.get(TransactionManager)
        transaction.begin()
        loaded = scope.get(TaskRepository).load(child)
        before = (loaded.id, loaded.title, loaded.version)
        if action == "delete":
            scope.get(EntitySaver).delete(loaded)
            scope.get(Session).flush()
        else:
            loaded.title = "" if action == "invalid_commit" else "Changed"
            loaded.touch()
            if action == "invalid_commit":
                with pytest.raises(IntegrityError):
                    transaction.commit()
        transaction.rollback()
        assert (loaded.id, loaded.title, loaded.version) == before
        assert scope.get(TaskRepository).load(child) is loaded
    assert loaded.id == child
    assert loaded.title == "Child"
    with container() as scope:
        assert (
            scope.get(GetTask).execute(TaskInput(child)).version == before[2]
        )


def test_new_entity_rollback_keeps_identity(container: Container) -> None:
    with container() as scope:
        project_id = (
            scope.get(CreateProject)
            .execute(CreateProjectInput("Test project"))
            .project_id
        )
    with container() as scope:
        transaction = scope.get(TransactionManager)
        transaction.begin()
        task = Task("New", TaskKind.EPIC, project_id=project_id)
        identity = task.id
        scope.get(EntitySaver).add(task)
        scope.get(Session).flush()
        transaction.rollback()
        assert task.id == identity
        state = inspect(task)
        assert state is not None
        assert state.transient
    with container() as scope:
        assert scope.get(GetBoard).execute(BoardInput()).total == 0


def test_concurrent_child_creation_serializes_invariants(
    container: Container,
) -> None:
    _, master, _ = seed(container)

    def create(index: int) -> UUID:
        with container() as scope:
            return (
                scope.get(CreateTask)
                .execute(
                    CreateTaskInput(
                        f"Child {index}",
                        TaskKind.SUBTASK,
                        master,
                    ),
                )
                .task_id
            )

    with ThreadPoolExecutor(max_workers=4) as executor:
        identities = list(executor.map(create, range(20)))
    assert len(set(identities)) == 20
    with container() as scope:
        assert scope.get(GetBoard).execute(BoardInput()).total == 21


def test_concurrent_edits_cannot_lose_updates(container: Container) -> None:
    _, _, child = seed(container)

    def update(prompt: str) -> bool:
        with container() as scope:
            try:
                scope.get(UpdateTask).execute(
                    UpdateTaskInput(child, 1, prompt=prompt),
                )
                return True
            except TaskConflict:
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ["First", "Second"]))
    assert sorted(results) == [False, True]
    with container() as scope:
        task = scope.get(GetTask).execute(TaskInput(child))
        assert task.version == 2
        assert task.prompt in {"First", "Second"}


def test_migrations_upgrade_downgrade_and_schema(
    container: Container,
    config: Config,
) -> None:
    engine = container.get(Engine)
    with engine.connect() as connection:
        constraints = inspect(connection).get_foreign_keys("tasks")
        assert any(
            item["options"].get("deferrable") is True for item in constraints
        )
        assert any(
            index["name"] == "ix_tasks_parent_position"
            for index in inspect(connection).get_indexes("tasks")
        )
    alembic = AlembicConfig()
    import eonarq.migrations

    alembic.set_main_option(
        "script_location",
        str(eonarq.migrations.__path__[0]),
    )
    with engine.begin() as connection:
        alembic.attributes["connection"] = connection
        command.downgrade(alembic, "base")
        assert "tasks" not in inspect(connection).get_table_names()
    migrate(config)
    with engine.connect() as connection:
        assert "tasks" in inspect(connection).get_table_names()


def test_closing_parent_and_adding_child_preserves_invariant(
    container: Container,
) -> None:
    _, master, child = seed(container)
    with container() as scope:
        scope.get(UpdateTask).execute(
            UpdateTaskInput(child, 1, status=TaskStatus.DONE),
        )
    with container() as scope:
        version = scope.get(GetTask).execute(TaskInput(master)).version

    def close_parent() -> None:
        with container() as scope, contextlib.suppress(TaskConflict):
            scope.get(UpdateTask).execute(
                UpdateTaskInput(master, version, status=TaskStatus.DONE),
            )

    def add_child() -> None:
        with container() as scope:
            scope.get(CreateTask).execute(
                CreateTaskInput("Next", TaskKind.SUBTASK, master),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(close_parent), executor.submit(add_child)]
        for future in futures:
            future.result()
    with container() as scope:
        assert (
            scope.get(GetTask).execute(TaskInput(master)).status
            != TaskStatus.DONE
        )
        assert scope.get(GetBoard).execute(BoardInput()).total == 2


def test_project_mapping_rollback_and_database_boundary(
    container: Container,
) -> None:
    _, master, _ = seed(container)
    with container() as scope:
        project_id = (
            scope.get(CreateProject)
            .execute(CreateProjectInput("Other"))
            .project_id
        )
    with container() as scope:
        transaction = scope.get(TransactionManager)
        transaction.begin()
        project = scope.get(TaskRepository).load_project(project_id)
        project.title = "Changed"
        project.version += 1
        scope.get(Session).flush()
        transaction.rollback()
        assert (project.title, project.version) == ("Other", 1)
    with container() as scope:
        transaction = scope.get(TransactionManager)
        transaction.begin()
        task = Task(
            "Cross project",
            TaskKind.SUBTASK,
            parent_id=master,
            project_id=project_id,
        )
        scope.get(EntitySaver).add(task)
        with pytest.raises(IntegrityError):
            transaction.commit()
        transaction.rollback()
    with container() as scope:
        project = scope.get(TaskReader).load_project(project_id)
        project.prompt = "Forbidden"
        with pytest.raises(InvalidTask, match="read-only"):
            scope.get(Session).commit()
        scope.get(Session).rollback()

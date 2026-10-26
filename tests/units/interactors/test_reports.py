from typing import cast

import pytest

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.dtos import (
    CreateTaskInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import InvalidTask, TaskConflict
from eonarq.planning.common.domain.invariants import ensure_report
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from eonarq.planning.query.application.dtos import TaskInput
from eonarq.planning.query.application.get import GetTask
from tests.units.fakes import MemoryStore, MemoryTaskReader


def test_report_creation_completion_editing_and_clear(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    assert child.report == ""
    report = "  # Results\nГотово: 12 checks passed.\n"
    created = CreateTask(store, store, store).execute(
        CreateTaskInput(
            title="Reported",
            kind=TaskKind.SUBTASK,
            parent_id=master.id,
            report=report,
        ),
    )
    assert store.load(created.task_id).report == report
    update = UpdateTask(store, store)
    update.execute(
        UpdateTaskInput(
            child.id,
            child.version,
            report=report,
            status=TaskStatus.DONE,
        ),
    )
    assert child.report == report
    assert child.status == TaskStatus.DONE
    assert epic.status == master.status == TaskStatus.TODO
    update.execute(
        UpdateTaskInput(child.id, child.version, prompt="New instructions"),
    )
    assert (
        GetTask(MemoryTaskReader(store)).execute(TaskInput(child.id)).report
        == report
    )
    update.execute(
        UpdateTaskInput(child.id, child.version, report="Revised results"),
    )
    assert child.status == TaskStatus.DONE
    update.execute(UpdateTaskInput(child.id, child.version, report=""))
    assert child.report == ""


def test_report_does_not_bypass_parent_completion(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    _, master, _ = tree
    with pytest.raises(TaskConflict, match="every child"):
        UpdateTask(store, store).execute(
            UpdateTaskInput(
                master.id,
                master.version,
                status=TaskStatus.DONE,
                report="Not finished",
            ),
        )
    assert master.report == ""
    assert master.status == TaskStatus.TODO


@pytest.mark.parametrize(
    "error",
    [RuntimeError("Commit failed"), GeneratorExit("Cancelled")],
)
def test_report_and_status_roll_back_together(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
    error: BaseException,
) -> None:
    child = tree[2]
    child.report = "Previous report"
    version = child.version
    store.commit_error = error
    with pytest.raises(type(error)):
        UpdateTask(store, store).execute(
            UpdateTaskInput(
                child.id,
                child.version,
                status=TaskStatus.DONE,
                report="Uncommitted",
            ),
        )
    assert (child.report, child.status, child.version) == (
        "Previous report",
        TaskStatus.TODO,
        version,
    )


@pytest.mark.parametrize(
    "report",
    [
        pytest.param("x" * 200001, id="too_long"),
        pytest.param(cast("str", 42), id="not_text"),
    ],
)
def test_report_validation_precedes_storage(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
    report: str,
) -> None:
    child = tree[2]
    before = store.begins
    with pytest.raises(InvalidTask, match="Report"):
        CreateTask(store, store, store).execute(
            CreateTaskInput(
                "Bad report",
                TaskKind.SUBTASK,
                tree[1].id,
                report=report,
            ),
        )
    with pytest.raises(InvalidTask, match="Report"):
        UpdateTask(store, store).execute(
            UpdateTaskInput(child.id, child.version, report=report),
        )
    with pytest.raises(InvalidTask, match="Report"):
        Task(
            "Bad report",
            TaskKind.EPIC,
            project_id=store.project.id,
            report=report,
        )
    assert store.begins == before


def test_report_accepts_empty_and_character_limit() -> None:
    ensure_report("")
    ensure_report("Я" * 200000)

from typing import cast
from uuid import UUID, uuid7

import pytest

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.dtos import CreateTaskInput
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import InvalidTask, TaskNotFound
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.dtos import BoardInput, TaskInput
from eonarq.planning.query.application.get import GetTask
from eonarq.planning.query.application.prompt import GetTaskPrompt
from tests.units.fakes import MemoryStore, MemoryTaskReader


def test_empty_board(store: MemoryStore) -> None:
    result = GetBoard(MemoryTaskReader(store)).execute(BoardInput())
    assert (result.done, result.total, result.percent) == (0, 0, 0)
    assert result.tasks == result.cells == ()
    assert result.flow.total == result.flow.wip == result.flow.blocked == 0
    assert result.flow.completion_percent == 0


def test_progress_counts_leaves_and_keeps_parent_completion_explicit(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    create = CreateTask(store, store, store)
    create.execute(
        CreateTaskInput("Second", TaskKind.SUBTASK, master.id, position=1),
    )
    child.status = TaskStatus.DONE
    result = GetBoard(MemoryTaskReader(store)).execute(BoardInput(epic.id))
    assert (result.done, result.total, result.percent) == (1, 2, 50)
    assert all(
        task.percent == 50
        for task in result.tasks
        if task.kind != TaskKind.SUBTASK
    )
    assert master.status == epic.status == TaskStatus.TODO
    assert result.cells[0].id == child.id
    assert all(
        cell.epic_id == epic.id and cell.master_id == master.id
        for cell in result.cells
    )


def test_empty_tasks_are_leaves_and_epic_scope_isolated(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic = tree[0]
    other = CreateTask(store, store, store).execute(
        CreateTaskInput("Empty", TaskKind.EPIC, position=1),
    )
    reader = GetBoard(MemoryTaskReader(store))
    assert reader.execute(BoardInput()).total == 2
    scoped = reader.execute(BoardInput(other.task_id))
    assert scoped.total == 1
    assert scoped.cells[0].master_id is None
    assert all(task.id != epic.id for task in scoped.tasks)


def test_invalid_board_scopes(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    reader = GetBoard(MemoryTaskReader(store))
    with pytest.raises(TaskNotFound):
        reader.execute(BoardInput(uuid7()))
    with pytest.raises(InvalidTask, match="epic"):
        reader.execute(BoardInput(tree[1].id))


def test_get_task_and_inherited_prompt(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    child = tree[2]
    reader = MemoryTaskReader(store)
    task = GetTask(reader).execute(TaskInput(child.id))
    assert task.prompt == "Subtask context"
    assert task.version == child.version
    result = GetTaskPrompt(reader).execute(TaskInput(child.id))
    assert (
        result.content.index("Epic context")
        < result.content.index("Master context")
        < result.content.index("Subtask context")
    )
    assert str(child.id) in result.content
    assert "Version: 1" in result.content
    tree[0].prompt = "Revised epic prompt"
    assert (
        "Revised epic prompt"
        in GetTaskPrompt(reader).execute(TaskInput(child.id)).content
    )


def test_get_task_missing(store: MemoryStore) -> None:
    reader = MemoryTaskReader(store)
    with pytest.raises(TaskNotFound):
        GetTask(reader).execute(TaskInput(uuid7()))
    with pytest.raises(TaskNotFound):
        GetTaskPrompt(reader).execute(TaskInput(uuid7()))


def test_query_ids_are_validated_without_transport(store: MemoryStore) -> None:
    with pytest.raises(InvalidTask, match="Task ID"):
        GetBoard(MemoryTaskReader(store)).execute(
            BoardInput(cast("UUID", "bad")),
        )


def test_agile_metrics_count_epics_and_direct_children_separately(
    store: MemoryStore,
) -> None:
    create = CreateTask(store, store, store)
    epics = []
    for status in TaskStatus:
        identity = create.execute(
            CreateTaskInput(status.value, TaskKind.EPIC),
        ).task_id
        epic = store.load(identity)
        epic.status = status
        epics.append(epic)
    master = store.load(
        create.execute(
            CreateTaskInput("Blocked master", TaskKind.MASTER, epics[0].id),
        ).task_id,
    )
    master.status = TaskStatus.BLOCKED
    child = store.load(
        create.execute(
            CreateTaskInput("Child", TaskKind.SUBTASK, master.id),
        ).task_id,
    )
    child.status = TaskStatus.IN_PROGRESS
    board = GetBoard(MemoryTaskReader(store))
    overview = board.execute(BoardInput())
    assert overview.flow.total == 4
    assert overview.flow.todo == overview.flow.in_progress == 1
    assert overview.flow.blocked == overview.flow.done == 1
    assert overview.flow.wip == 2
    assert overview.flow.completion_percent == 25
    scoped = board.execute(BoardInput(epics[0].id))
    assert scoped.flow.total == scoped.flow.blocked == scoped.flow.wip == 1
    assert scoped.flow.todo == scoped.flow.in_progress == scoped.flow.done == 0
    epic_summary = next(
        task for task in overview.tasks if task.id == epics[0].id
    )
    assert epic_summary.flow == scoped.flow
    master_summary = next(
        task for task in scoped.tasks if task.id == master.id
    )
    assert master_summary.flow.in_progress == 1
    assert master_summary.flow.blocked == 0

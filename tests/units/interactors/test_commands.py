from typing import cast
from uuid import UUID, uuid7

import pytest

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.delete import DeleteTask
from eonarq.planning.command.application.dtos import (
    CreateTaskInput,
    DeleteTaskInput,
    MoveTaskInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import (
    InvalidTask,
    TaskConflict,
    TaskNotFound,
)
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from tests.units.fakes import MemoryStore


def test_create_trims_text_and_preserves_prompt(store: MemoryStore) -> None:
    result = CreateTask(store, store, store).execute(
        CreateTaskInput(
            "  Epic  ",
            TaskKind.EPIC,
            prompt=" # Exact prompt\n",
            project_id=store.project.id,
        ),
    )
    task = store.load(result.task_id)
    assert task.title == "Epic"
    assert task.prompt == " # Exact prompt\n"
    assert task.id.version == 7
    assert store.commits == 1


@pytest.mark.parametrize("kind", [TaskKind.MASTER, TaskKind.SUBTASK])
def test_create_requires_parent(store: MemoryStore, kind: TaskKind) -> None:
    with pytest.raises(InvalidTask, match="Hierarchy"):
        CreateTask(store, store, store).execute(CreateTaskInput("Task", kind))
    assert not store.tasks
    assert store.rollbacks == 1


def test_create_missing_parent_rolls_back(store: MemoryStore) -> None:
    with pytest.raises(TaskNotFound):
        CreateTask(store, store, store).execute(
            CreateTaskInput("Task", TaskKind.MASTER, uuid7()),
        )
    assert store.rollbacks == 1


def test_cannot_skip_hierarchy_or_parent_an_epic(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, _, child = tree
    create = CreateTask(store, store, store)
    for kind, parent in [
        (TaskKind.SUBTASK, epic.id),
        (TaskKind.EPIC, epic.id),
        (TaskKind.MASTER, child.id),
    ]:
        with pytest.raises(InvalidTask, match="Hierarchy"):
            create.execute(CreateTaskInput("Wrong level", kind, parent))
    assert len(store.tasks) == 3


def test_creation_under_completed_parents_reopens_ancestors(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    for task in tree:
        task.status = TaskStatus.DONE
    CreateTask(store, store, store).execute(
        CreateTaskInput("Next", TaskKind.SUBTASK, master.id),
    )
    assert epic.status == master.status == TaskStatus.IN_PROGRESS
    assert child.status == TaskStatus.DONE


def test_update_edits_prompt_order_and_status(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    child = tree[2]
    result = UpdateTask(store, store).execute(
        UpdateTaskInput(
            child.id,
            child.version,
            " Renamed ",
            "# New prompt",
            TaskStatus.BLOCKED,
            12,
        ),
    )
    assert (child.title, child.prompt, child.status, child.position) == (
        "Renamed",
        "# New prompt",
        TaskStatus.BLOCKED,
        12,
    )
    assert result.version == 2


def test_explicit_parent_completion_and_reopening(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    update = UpdateTask(store, store)
    with pytest.raises(TaskConflict, match="every child"):
        update.execute(
            UpdateTaskInput(master.id, master.version, status=TaskStatus.DONE),
        )
    update.execute(
        UpdateTaskInput(child.id, child.version, status=TaskStatus.DONE),
    )
    assert master.status == TaskStatus.TODO
    update.execute(
        UpdateTaskInput(master.id, master.version, status=TaskStatus.DONE),
    )
    assert epic.status == TaskStatus.TODO
    update.execute(
        UpdateTaskInput(epic.id, epic.version, status=TaskStatus.DONE),
    )
    update.execute(
        UpdateTaskInput(child.id, child.version, status=TaskStatus.TODO),
    )
    assert epic.status == master.status == TaskStatus.IN_PROGRESS


def test_empty_parent_can_close_and_omitted_fields_stay_intact(
    store: MemoryStore,
) -> None:
    create = CreateTask(store, store, store)
    task = store.load(
        create.execute(
            CreateTaskInput(
                "Epic",
                TaskKind.EPIC,
                prompt="Exact",
                project_id=store.project.id,
            ),
        ).task_id,
    )
    UpdateTask(store, store).execute(
        UpdateTaskInput(task.id, 1, status=TaskStatus.DONE),
    )
    assert task.status == TaskStatus.DONE
    assert task.prompt == "Exact"
    assert task.position == 0


def test_stale_edit_does_not_overwrite(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    child = tree[2]
    update = UpdateTask(store, store)
    update.execute(UpdateTaskInput(child.id, 1, prompt="Newer"))
    with pytest.raises(TaskConflict, match="reload"):
        update.execute(UpdateTaskInput(child.id, 1, prompt="Stale"))
    assert child.prompt == "Newer"
    assert child.version == 2


def test_move_reparents_and_reopens_target(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, old_parent, child = tree
    new_parent = store.load(
        CreateTask(store, store, store)
        .execute(CreateTaskInput("Target", TaskKind.MASTER, epic.id))
        .task_id,
    )
    new_parent.status = TaskStatus.DONE
    before = old_parent.version
    MoveTask(store, store).execute(
        MoveTaskInput(child.id, new_parent.id, child.version),
    )
    assert child.parent_id == new_parent.id
    assert old_parent.version == before + 1
    assert new_parent.status == TaskStatus.IN_PROGRESS


def test_move_done_child_keeps_completed_target_and_same_parent_is_valid(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    other = store.load(
        CreateTask(store, store, store)
        .execute(CreateTaskInput("Target", TaskKind.MASTER, epic.id))
        .task_id,
    )
    child.status = other.status = TaskStatus.DONE
    move = MoveTask(store, store)
    move.execute(MoveTaskInput(child.id, other.id, child.version))
    assert other.status == TaskStatus.DONE
    move.execute(MoveTaskInput(child.id, other.id, child.version))
    assert child.parent_id != master.id


def test_move_master_between_epics(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    target = store.load(
        CreateTask(store, store, store)
        .execute(
            CreateTaskInput(
                "Another epic",
                TaskKind.EPIC,
                project_id=store.project.id,
            ),
        )
        .task_id,
    )
    MoveTask(store, store).execute(
        MoveTaskInput(master.id, target.id, master.version),
    )
    assert master.parent_id == target.id
    assert child.parent_id == master.id
    assert epic.id != master.parent_id


def test_invalid_move_rolls_back(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    for task, parent in [
        (child, epic),
        (epic, master),
        (master, child),
        (child, child),
    ]:
        with pytest.raises(InvalidTask, match="Hierarchy"):
            MoveTask(store, store).execute(
                MoveTaskInput(task.id, parent.id, task.version),
            )
    assert child.parent_id == master.id
    assert master.parent_id == epic.id


def test_delete_requires_explicit_recursive_choice(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic = tree[0]
    delete = DeleteTask(store, store, store)
    with pytest.raises(TaskConflict, match="recursive"):
        delete.execute(DeleteTaskInput(epic.id, epic.version))
    assert len(store.tasks) == 3
    delete.execute(DeleteTaskInput(epic.id, epic.version, recursive=True))
    assert not store.tasks


def test_delete_leaf_preserves_parent(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    _, master, child = tree
    before = master.version
    DeleteTask(store, store, store).execute(
        DeleteTaskInput(child.id, child.version),
    )
    assert len(store.tasks) == 2
    assert store.load(master.id).version == before + 1


@pytest.mark.parametrize("operation", ["create", "update", "move", "delete"])
@pytest.mark.parametrize(
    "error",
    [RuntimeError("Commit failed"), GeneratorExit("Cancelled")],
)
def test_every_mutation_rolls_back_commit_failure(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
    operation: str,
    error: BaseException,
) -> None:
    epic, master, child = tree
    old_version = child.version
    store.commit_error = error
    actions = {
        "create": lambda: CreateTask(store, store, store).execute(
            CreateTaskInput("New", TaskKind.SUBTASK, master.id),
        ),
        "update": lambda: UpdateTask(store, store).execute(
            UpdateTaskInput(child.id, child.version, prompt="Not committed"),
        ),
        "move": lambda: MoveTask(store, store).execute(
            MoveTaskInput(master.id, epic.id, master.version),
        ),
        "delete": lambda: DeleteTask(store, store, store).execute(
            DeleteTaskInput(epic.id, epic.version, True),
        ),
    }
    with pytest.raises(type(error)):
        actions[operation]()
    assert len(store.tasks) == 3
    assert child.version == old_version
    assert child.prompt == "Subtask context"
    assert store.rollbacks == 1
    assert store.load(child.id) is child


@pytest.mark.parametrize("operation", ["update", "move", "delete"])
def test_missing_targets_roll_back(store: MemoryStore, operation: str) -> None:
    actions = {
        "update": lambda: UpdateTask(store, store).execute(
            UpdateTaskInput(uuid7(), 1),
        ),
        "move": lambda: MoveTask(store, store).execute(
            MoveTaskInput(uuid7(), uuid7(), 1),
        ),
        "delete": lambda: DeleteTask(store, store, store).execute(
            DeleteTaskInput(uuid7(), 1),
        ),
    }
    with pytest.raises(TaskNotFound):
        actions[operation]()
    assert store.rollbacks == 1


@pytest.mark.parametrize("operation", ["move", "delete"])
def test_stale_move_or_delete_is_rejected(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
    operation: str,
) -> None:
    epic, master, _ = tree
    actions = {
        "move": lambda: MoveTask(store, store).execute(
            MoveTaskInput(master.id, epic.id, 999),
        ),
        "delete": lambda: DeleteTask(store, store, store).execute(
            DeleteTaskInput(master.id, 999, True),
        ),
    }
    with pytest.raises(TaskConflict):
        actions[operation]()
    assert len(store.tasks) == 3


def test_validation_runs_before_storage(store: MemoryStore) -> None:
    with pytest.raises(InvalidTask):
        CreateTask(store, store, store).execute(
            CreateTaskInput(" ", TaskKind.EPIC, project_id=store.project.id),
        )
    with pytest.raises(InvalidTask):
        UpdateTask(store, store).execute(UpdateTaskInput(uuid7(), 0))
    with pytest.raises(InvalidTask):
        MoveTask(store, store).execute(
            MoveTaskInput(uuid7(), cast("UUID", "bad"), 1),
        )
    with pytest.raises(InvalidTask):
        DeleteTask(store, store, store).execute(
            DeleteTaskInput(uuid7(), 1, cast("bool", "true")),
        )
    assert store.begins == 0


def test_begin_failure_is_rolled_back(store: MemoryStore) -> None:
    store.begin_error = RuntimeError("Busy")
    with pytest.raises(RuntimeError, match="Busy"):
        CreateTask(store, store, store).execute(
            CreateTaskInput(
                "Title",
                TaskKind.EPIC,
                project_id=store.project.id,
            ),
        )
    assert store.rollbacks == 1


def test_application_validates_non_http_inputs(store: MemoryStore) -> None:
    create = CreateTask(store, store, store)
    with pytest.raises(InvalidTask, match="kind"):
        create.execute(CreateTaskInput("Title", cast("TaskKind", "bad")))
    with pytest.raises(InvalidTask, match="Parent ID"):
        create.execute(
            CreateTaskInput("Title", TaskKind.MASTER, cast("UUID", "bad")),
        )
    with pytest.raises(InvalidTask, match="Task ID"):
        UpdateTask(store, store).execute(
            UpdateTaskInput(cast("UUID", "bad"), 1),
        )
    assert store.begins == 0

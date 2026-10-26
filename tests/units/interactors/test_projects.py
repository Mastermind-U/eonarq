from typing import cast
from uuid import UUID, uuid7

import pytest

from eonarq.planning.command.application.clear_cancelled import ClearCancelled
from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.create_project import CreateProject
from eonarq.planning.command.application.dtos import (
    ClearCancelledInput,
    CreateProjectInput,
    CreateTaskInput,
    MoveTaskInput,
    UpdateProjectInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.application.update_project import UpdateProject
from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import (
    InvalidTask,
    TaskConflict,
    TaskNotFound,
)
from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)
from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.dtos import (
    BoardInput,
    ProjectsInput,
    TaskInput,
)
from eonarq.planning.query.application.projects import ListProjects
from eonarq.planning.query.application.prompt import GetTaskPrompt
from tests.units.fakes import MemoryStore, MemoryTaskReader


def test_projects_inherit_instructions_and_isolate_board(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    project = CreateProject(store, store).execute(
        CreateProjectInput(" Other ", "Other instructions"),
    )
    other = CreateTask(store, store, store).execute(
        CreateTaskInput(
            "Other epic",
            TaskKind.EPIC,
            project_id=project.project_id,
            action=TaskAction.RESEARCH,
        ),
    )
    reader = MemoryTaskReader(store)
    projects = ListProjects(reader).execute(ProjectsInput())
    assert {item.title for item in projects} == {"Test project", "Other"}
    result = GetBoard(reader).execute(
        BoardInput(project_id=project.project_id),
    )
    assert [item.id for item in result.tasks] == [other.task_id]
    assert result.tasks[0].action == TaskAction.RESEARCH
    assert result.flow.total == 1
    assert (
        len(
            GetBoard(reader)
            .execute(BoardInput(project_id=store.project.id))
            .tasks,
        )
        == 3
    )
    UpdateProject(store, store).execute(
        UpdateProjectInput(
            project_id=project.project_id,
            expected_version=1,
            title="Renamed",
            prompt="Revised project",
        ),
    )
    assert (
        "Revised project"
        in GetTaskPrompt(reader).execute(TaskInput(other.task_id)).content
    )
    assert (
        "Other instructions"
        not in GetTaskPrompt(reader).execute(TaskInput(tree[2].id)).content
    )
    with pytest.raises(TaskConflict):
        UpdateProject(store, store).execute(
            UpdateProjectInput(project.project_id, 1, "Stale"),
        )


def test_project_constraints_apply_without_transport(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    create = CreateTask(store, store, store)
    with pytest.raises(InvalidTask, match="requires a project"):
        create.execute(CreateTaskInput("Epic", TaskKind.EPIC))
    with pytest.raises(TaskNotFound, match="Project"):
        create.execute(
            CreateTaskInput("Epic", TaskKind.EPIC, project_id=uuid7()),
        )
    other = CreateProject(store, store).execute(CreateProjectInput("Other"))
    with pytest.raises(InvalidTask, match="one project"):
        create.execute(
            CreateTaskInput(
                "Child",
                TaskKind.SUBTASK,
                tree[1].id,
                project_id=other.project_id,
            ),
        )
    target = create.execute(
        CreateTaskInput("Target", TaskKind.EPIC, project_id=other.project_id),
    )
    with pytest.raises(InvalidTask, match="across projects"):
        MoveTask(store, store).execute(
            MoveTaskInput(tree[1].id, target.task_id, tree[1].version),
        )
    board = GetBoard(MemoryTaskReader(store))
    with pytest.raises(TaskNotFound):
        board.execute(BoardInput(tree[0].id, other.project_id))
    with pytest.raises(TaskNotFound):
        board.execute(BoardInput(project_id=uuid7()))
    with pytest.raises(InvalidTask):
        ClearCancelled(store, store, store).execute(
            ClearCancelledInput(cast("UUID", "bad")),
        )
    with pytest.raises(InvalidTask, match="action"):
        UpdateTask(store, store).execute(
            UpdateTaskInput(
                tree[2].id,
                tree[2].version,
                action=cast("TaskAction", "OTHER"),
            ),
        )


def test_cancellation_reopening_progress_and_project_clear(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    other_project = CreateProject(store, store).execute(
        CreateProjectInput("Other"),
    )
    other = CreateTask(store, store, store).execute(
        CreateTaskInput(
            "Other",
            TaskKind.EPIC,
            project_id=other_project.project_id,
        ),
    )
    update = UpdateTask(store, store)
    update.execute(
        UpdateTaskInput(other.task_id, 1, status=TaskStatus.CANCELLED),
    )
    update.execute(
        UpdateTaskInput(
            child.id,
            child.version,
            status=TaskStatus.DONE,
            action=TaskAction.CHECK,
        ),
    )
    update.execute(
        UpdateTaskInput(epic.id, epic.version, status=TaskStatus.CANCELLED),
    )
    assert all(task.status == TaskStatus.CANCELLED for task in tree)
    board = GetBoard(MemoryTaskReader(store)).execute(
        BoardInput(project_id=store.project.id),
    )
    assert board.total == board.done == board.percent == 0
    assert board.flow.cancelled == 3
    assert len(board.cells) == 1
    update.execute(
        UpdateTaskInput(child.id, child.version, status=TaskStatus.TODO),
    )
    assert epic.status == master.status == TaskStatus.IN_PROGRESS
    assert child.action == TaskAction.CHECK
    update.execute(
        UpdateTaskInput(
            master.id,
            master.version,
            status=TaskStatus.CANCELLED,
        ),
    )
    update.execute(
        UpdateTaskInput(epic.id, epic.version, status=TaskStatus.DONE),
    )
    result = ClearCancelled(store, store, store).execute(
        ClearCancelledInput(store.project.id),
    )
    assert result.deleted == 2
    assert set(store.tasks) == {epic.id, other.task_id}
    assert store.load(other.task_id).status == TaskStatus.CANCELLED
    assert (
        ClearCancelled(store, store, store)
        .execute(ClearCancelledInput(store.project.id))
        .deleted
        == 0
    )


@pytest.mark.parametrize(
    "operation",
    ["create_project", "update_project", "cancel", "clear"],
)
@pytest.mark.parametrize(
    "error",
    [RuntimeError("Commit failed"), GeneratorExit("Cancelled")],
)
def test_project_operations_restore_state_on_failure(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
    operation: str,
    error: BaseException,
) -> None:
    epic, _, child = tree
    if operation == "clear":
        UpdateTask(store, store).execute(
            UpdateTaskInput(
                epic.id,
                epic.version,
                status=TaskStatus.CANCELLED,
            ),
        )
    versions = [task.version for task in tree]
    statuses = [task.status for task in tree]
    store.commit_error = error
    actions = {
        "create_project": lambda: CreateProject(store, store).execute(
            CreateProjectInput("New project"),
        ),
        "update_project": lambda: UpdateProject(store, store).execute(
            UpdateProjectInput(store.project.id, 1, "Changed", "Changed"),
        ),
        "cancel": lambda: UpdateTask(store, store).execute(
            UpdateTaskInput(
                epic.id,
                epic.version,
                status=TaskStatus.CANCELLED,
                action=TaskAction.RESEARCH,
            ),
        ),
        "clear": lambda: ClearCancelled(store, store, store).execute(
            ClearCancelledInput(store.project.id),
        ),
    }
    with pytest.raises(type(error)):
        actions[operation]()
    assert len(store.tasks) == 3
    assert len(store.projects) == 1
    assert store.project.title == "Test project"
    assert [task.version for task in tree] == versions
    assert [task.status for task in tree] == statuses
    assert store.load(child.id) is child


def test_done_child_reopens_cancelled_ancestors(
    store: MemoryStore,
    tree: tuple[Task, Task, Task],
) -> None:
    epic, master, child = tree
    update = UpdateTask(store, store)
    update.execute(
        UpdateTaskInput(epic.id, epic.version, status=TaskStatus.CANCELLED),
    )
    update.execute(
        UpdateTaskInput(child.id, child.version, status=TaskStatus.DONE),
    )
    assert epic.status == master.status == TaskStatus.IN_PROGRESS
    assert child.status == TaskStatus.DONE
    assert (
        ClearCancelled(store, store, store)
        .execute(ClearCancelledInput(store.project.id))
        .deleted
        == 0
    )

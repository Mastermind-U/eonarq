from typing import cast
from uuid import UUID

import pytest

from eonarq.planning.command.domain.entities import Task
from eonarq.planning.common.domain.exceptions import InvalidTask, TaskConflict
from eonarq.planning.common.domain.invariants import (
    ensure_parent,
    ensure_position,
    ensure_status,
    ensure_text,
)
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from eonarq.shared_kernel.infrastructure.config import Config, load_config


@pytest.mark.parametrize("title", ["", "  ", "x" * 201])
def test_title_bounds(title: str) -> None:
    with pytest.raises(InvalidTask, match="Title"):
        ensure_text(title, "")


def test_prompt_is_text_and_has_a_bound() -> None:
    with pytest.raises(InvalidTask, match="Prompt"):
        ensure_text("Title", "x" * 200001)
    ensure_text("Title", "x" * 200000)


@pytest.mark.parametrize("position", [-1, 1000001, True])
def test_position_rejects_invalid_values(position: int) -> None:
    with pytest.raises(InvalidTask, match="Position"):
        ensure_position(position)


@pytest.mark.parametrize(
    ("kind", "parent"),
    [
        (TaskKind.EPIC, None),
        (TaskKind.MASTER, TaskKind.EPIC),
        (TaskKind.SUBTASK, TaskKind.MASTER),
    ],
)
def test_valid_hierarchy(kind: TaskKind, parent: TaskKind | None) -> None:
    ensure_parent(kind, parent)


def test_invalid_status_and_kind_are_rejected() -> None:
    with pytest.raises(InvalidTask, match="status"):
        ensure_status(cast("TaskStatus", "unknown"))
    with pytest.raises(InvalidTask, match="Hierarchy"):
        ensure_parent(cast("TaskKind", "unknown"), None)


def test_identity_normalization_versions_and_reopen() -> None:
    task = Task("  Title  ", TaskKind.EPIC, project_id=UUID(int=1))
    assert task.title == "Title"
    assert task.id.version == 7
    before = task.updated_at
    with pytest.raises(TaskConflict, match="reload"):
        task.ensure_version(2)
    task.status = TaskStatus.DONE
    task.reopen()
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.version == 2
    assert task.updated_at >= before
    task.reopen()
    assert task.version == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"DATABASE_URL": "postgresql://localhost/test"},
        {"DATABASE_URL": "sqlite:///:memory:"},
        {"DATABASE_URL": "sqlite:///"},
        {"DATABASE_URL": "sqlite:///file:db?mode=memory&uri=true"},
        {"PORT": 0},
        {"PORT": 65536},
        {"HOST": ""},
        {"ALLOWED_HOSTS": "*"},
        {"ALLOWED_HOSTS": ""},
    ],
)
def test_invalid_configuration(kwargs: dict[str, str | int]) -> None:
    with pytest.raises(
        ValueError,
        match="DATABASE_URL|HOST|PORT|ALLOWED_HOSTS",
    ):
        Config(**kwargs)  # type: ignore[arg-type]


def test_environment_config_is_fresh_and_does_not_interpolate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EONARQ_PORT", "8766")
    monkeypatch.setenv(
        "EONARQ_DATABASE_URL",
        "sqlite:///./$EONARQ_PORT.sqlite3",
    )
    assert load_config().PORT == 8766
    assert "$EONARQ_PORT" in load_config().DATABASE_URL
    monkeypatch.setenv("EONARQ_PORT", "8767")
    assert load_config().PORT == 8767

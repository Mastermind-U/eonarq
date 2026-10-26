from eonarq.planning.common.domain.exceptions import InvalidTask
from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)


def ensure_text(title: str, prompt: str) -> None:
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise InvalidTask("Title must contain 1–200 characters")
    if not isinstance(prompt, str) or len(prompt) > 200_000:
        raise InvalidTask("Prompt must contain at most 200,000 characters")


def ensure_position(position: int) -> None:
    if type(position) is not int or not 0 <= position <= 1_000_000:
        raise InvalidTask(
            "Position must be an integer between 0 and 1,000,000",
        )


def ensure_status(status: TaskStatus) -> None:
    if not isinstance(status, TaskStatus):
        raise InvalidTask("Unknown task status")


def ensure_action(action: TaskAction) -> None:
    if not isinstance(action, TaskAction):
        raise InvalidTask("Unknown task action")


def ensure_parent(kind: TaskKind, parent_kind: TaskKind | None) -> None:
    expected = {
        TaskKind.EPIC: None,
        TaskKind.MASTER: TaskKind.EPIC,
        TaskKind.SUBTASK: TaskKind.MASTER,
    }
    if not isinstance(kind, TaskKind) or parent_kind != expected[kind]:
        raise InvalidTask("Hierarchy must be epic → master → subtask")

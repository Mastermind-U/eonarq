from enum import StrEnum


class TaskKind(StrEnum):
    EPIC = "epic"
    MASTER = "master"
    SUBTASK = "subtask"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskAction(StrEnum):
    RESEARCH = "RESEARCH"
    ACTION = "ACTION"
    CHECK = "CHECK"

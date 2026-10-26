from dishka import Provider, Scope, provide, provide_all

from eonarq.planning.command.application.clear_cancelled import ClearCancelled
from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.create_project import CreateProject
from eonarq.planning.command.application.delete import DeleteTask
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.application.update_project import UpdateProject
from eonarq.planning.command.infrastructure.repository import (
    SQLiteTaskRepository,
)


class PlanningCommandProvider(Provider):
    repository = provide(
        SQLiteTaskRepository,
        provides=TaskRepository,
        scope=Scope.REQUEST,
    )
    interactors = provide_all(
        CreateTask,
        UpdateTask,
        MoveTask,
        DeleteTask,
        CreateProject,
        UpdateProject,
        ClearCancelled,
        scope=Scope.REQUEST,
    )

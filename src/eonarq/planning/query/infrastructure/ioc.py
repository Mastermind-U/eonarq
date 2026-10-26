from dishka import Provider, Scope, provide, provide_all

from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.application.get import GetTask
from eonarq.planning.query.application.projects import ListProjects
from eonarq.planning.query.application.prompt import GetTaskPrompt
from eonarq.planning.query.infrastructure.reader import SQLiteTaskReader


class PlanningQueryProvider(Provider):
    reader = provide(
        SQLiteTaskReader,
        provides=TaskReader,
        scope=Scope.REQUEST,
    )
    interactors = provide_all(
        GetBoard,
        GetTask,
        GetTaskPrompt,
        ListProjects,
        scope=Scope.REQUEST,
    )

from uuid import UUID

from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter

from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.dtos import (
    BoardInput,
    BoardOutput,
    ProjectData,
    ProjectsInput,
    PromptOutput,
    TaskInput,
    TaskOutput,
)
from eonarq.planning.query.application.get import GetTask
from eonarq.planning.query.application.projects import ListProjects
from eonarq.planning.query.application.prompt import GetTaskPrompt

router = APIRouter(
    prefix="/api/planning/q",
    tags=["Planning queries"],
    route_class=DishkaSyncRoute,
)


@router.get("/board")
def get_board(
    interactor: FromDishka[GetBoard],
    epic_id: UUID | None = None,
    project_id: UUID | None = None,
) -> BoardOutput:
    return interactor.execute(BoardInput(epic_id, project_id))


@router.get("/projects")
def list_projects(
    interactor: FromDishka[ListProjects],
) -> tuple[ProjectData, ...]:
    return interactor.execute(ProjectsInput())


@router.get("/tasks/{task_id}")
def get_task(task_id: UUID, interactor: FromDishka[GetTask]) -> TaskOutput:
    return interactor.execute(TaskInput(task_id))


@router.get("/tasks/{task_id}/prompt")
def get_task_prompt(
    task_id: UUID,
    interactor: FromDishka[GetTaskPrompt],
) -> PromptOutput:
    return interactor.execute(TaskInput(task_id))

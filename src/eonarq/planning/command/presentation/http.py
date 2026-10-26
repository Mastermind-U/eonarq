from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter

from eonarq.planning.command.application.clear_cancelled import ClearCancelled
from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.create_project import CreateProject
from eonarq.planning.command.application.delete import DeleteTask
from eonarq.planning.command.application.dtos import (
    ClearCancelledInput,
    ClearCancelledOutput,
    CreateProjectInput,
    CreateTaskInput,
    DeleteTaskInput,
    MoveTaskInput,
    MutationOutput,
    ProjectMutationOutput,
    UpdateProjectInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.application.update_project import UpdateProject

router = APIRouter(
    prefix="/api/planning/c",
    tags=["Planning commands"],
    route_class=DishkaSyncRoute,
)


@router.post("/create", status_code=201)
def create_task(
    data: CreateTaskInput,
    interactor: FromDishka[CreateTask],
) -> MutationOutput:
    return interactor.execute(data)


@router.post("/update")
def update_task(
    data: UpdateTaskInput,
    interactor: FromDishka[UpdateTask],
) -> MutationOutput:
    return interactor.execute(data)


@router.post("/move")
def move_task(
    data: MoveTaskInput,
    interactor: FromDishka[MoveTask],
) -> MutationOutput:
    return interactor.execute(data)


@router.post("/delete")
def delete_task(
    data: DeleteTaskInput,
    interactor: FromDishka[DeleteTask],
) -> MutationOutput:
    return interactor.execute(data)


@router.post("/projects/create", status_code=201)
def create_project(
    data: CreateProjectInput,
    interactor: FromDishka[CreateProject],
) -> ProjectMutationOutput:
    return interactor.execute(data)


@router.post("/projects/update")
def update_project(
    data: UpdateProjectInput,
    interactor: FromDishka[UpdateProject],
) -> ProjectMutationOutput:
    return interactor.execute(data)


@router.post("/clear-cancelled")
def clear_cancelled(
    data: ClearCancelledInput,
    interactor: FromDishka[ClearCancelled],
) -> ClearCancelledOutput:
    return interactor.execute(data)

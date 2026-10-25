from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter

from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.delete import DeleteTask
from eonarq.planning.command.application.dtos import (
    CreateTaskInput,
    DeleteTaskInput,
    MoveTaskInput,
    MutationOutput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask

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

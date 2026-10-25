from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from eonarq.planning.common.domain.exceptions import (
    PlanningException,
    TaskConflict,
    TaskNotFound,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlanningException)
    def planning_error(
        _request: Request,
        error: PlanningException,
    ) -> JSONResponse:
        status = (
            404
            if isinstance(error, TaskNotFound)
            else 409
            if isinstance(error, TaskConflict)
            else 400
        )
        return JSONResponse({"detail": str(error)}, status_code=status)

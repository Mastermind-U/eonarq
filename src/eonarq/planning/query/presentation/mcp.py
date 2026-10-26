import json
from dataclasses import asdict
from typing import Any
from uuid import UUID

from dishka import Container
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from eonarq.planning.common.domain.types import TaskKind
from eonarq.planning.query.application.board import GetBoard
from eonarq.planning.query.application.dtos import (
    BoardInput,
    ProjectsInput,
    TaskInput,
)
from eonarq.planning.query.application.get import GetTask
from eonarq.planning.query.application.projects import ListProjects
from eonarq.planning.query.application.prompt import GetTaskPrompt
from eonarq.shared_kernel.presentation.mcp import run_in_request


def register_query_tools(server: FastMCP, container: Container) -> None:
    readonly = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @server.tool(annotations=readonly)
    async def list_epics(
        project_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """List epic titles, versions, statuses and leaf-task progress."""
        board = await run_in_request(
            container,
            lambda scope: scope.get(GetBoard).execute(
                BoardInput(project_id=project_id),
            ),
        )
        return [
            asdict(task) for task in board.tasks if task.kind == TaskKind.EPIC
        ]

    @server.tool(annotations=readonly)
    async def get_board(
        epic_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Read the task tree and progress, optionally for one epic.

        Retrieve editable prompts separately with get_task.
        """
        result = await run_in_request(
            container,
            lambda scope: scope.get(GetBoard).execute(
                BoardInput(epic_id, project_id),
            ),
        )
        return asdict(result)

    @server.tool(annotations=readonly)
    async def list_projects() -> list[dict[str, Any]]:
        """List project IDs, editable shared prompts and current versions."""
        projects = await run_in_request(
            container,
            lambda scope: scope.get(ListProjects).execute(ProjectsInput()),
        )
        return [asdict(project) for project in projects]

    @server.tool(annotations=readonly)
    async def get_task(task_id: UUID) -> dict[str, Any]:
        """Read a task, its editable prompt and its current version."""
        result = await run_in_request(
            container,
            lambda scope: scope.get(GetTask).execute(TaskInput(task_id)),
        )
        return asdict(result)

    @server.tool(annotations=readonly)
    async def get_task_prompt(task_id: UUID) -> str:
        """Read the task prompt with inherited epic/master instructions."""
        result = await run_in_request(
            container,
            lambda scope: scope.get(GetTaskPrompt).execute(TaskInput(task_id)),
        )
        return result.content

    @server.prompt()
    async def work_on_task(task_id: UUID) -> str:
        """Load the current epic/master/subtask prompt chain."""
        return await get_task_prompt(task_id)

    @server.resource("eonarq://epics")
    async def epics_resource() -> str:
        epics = await list_epics()
        return json.dumps(epics, default=str)

    @server.resource("eonarq://tasks/{task_id}")
    async def task_resource(task_id: UUID) -> str:
        return json.dumps(await get_task(task_id), default=str)

from dataclasses import asdict
from typing import Any
from uuid import UUID

from dishka import Container
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from eonarq.planning.command.application.clear_cancelled import ClearCancelled
from eonarq.planning.command.application.create import CreateTask
from eonarq.planning.command.application.create_project import CreateProject
from eonarq.planning.command.application.delete import DeleteTask
from eonarq.planning.command.application.dtos import (
    ClearCancelledInput,
    CreateProjectInput,
    CreateTaskInput,
    DeleteTaskInput,
    MoveTaskInput,
    UpdateProjectInput,
    UpdateTaskInput,
)
from eonarq.planning.command.application.move import MoveTask
from eonarq.planning.command.application.update import UpdateTask
from eonarq.planning.command.application.update_project import UpdateProject
from eonarq.planning.common.domain.types import (
    TaskAction,
    TaskKind,
    TaskStatus,
)
from eonarq.shared_kernel.presentation.mcp import run_in_request


def register_command_tools(server: FastMCP, container: Container) -> None:
    mutation = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )

    @server.tool(annotations=mutation)
    async def create_task(
        title: str,
        kind: TaskKind,
        parent_id: UUID | None = None,
        prompt: str = "",
        position: int = 0,
        project_id: UUID | None = None,
        action: TaskAction = TaskAction.ACTION,
    ) -> dict[str, Any]:
        """Create a task in the three-level hierarchy.

        An epic has master tasks; a master has subtasks.
        Prompts are editable Markdown text.
        """
        data = CreateTaskInput(
            title,
            kind,
            parent_id,
            prompt,
            position,
            project_id,
            action,
        )
        return await run_in_request(
            container,
            lambda scope: asdict(scope.get(CreateTask).execute(data)),
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def update_task(
        task_id: UUID,
        expected_version: int,
        title: str | None = None,
        prompt: str | None = None,
        status: TaskStatus | None = None,
        position: int | None = None,
        action: TaskAction | None = None,
    ) -> dict[str, Any]:
        """Edit a task or its prompt.

        Get the latest version first. Close children before their parent.
        Reopening a child reopens completed ancestors.
        """
        data = UpdateTaskInput(
            task_id,
            expected_version,
            title,
            prompt,
            status,
            position,
            action,
        )
        return await run_in_request(
            container,
            lambda scope: asdict(scope.get(UpdateTask).execute(data)),
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def move_task(
        task_id: UUID,
        parent_id: UUID,
        expected_version: int,
    ) -> dict[str, Any]:
        """Move a master to an epic or a subtask to a master.

        The three-level hierarchy is preserved.
        """
        data = MoveTaskInput(task_id, parent_id, expected_version)
        return await run_in_request(
            container,
            lambda scope: asdict(scope.get(MoveTask).execute(data)),
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def delete_task(
        task_id: UUID,
        expected_version: int,
        recursive: bool = False,
    ) -> dict[str, Any]:
        """Delete a task using its current version.

        Deleting descendants requires recursive=true.
        """
        data = DeleteTaskInput(task_id, expected_version, recursive)
        return await run_in_request(
            container,
            lambda scope: asdict(scope.get(DeleteTask).execute(data)),
        )

    @server.tool(annotations=mutation)
    async def create_project(title: str, prompt: str = "") -> dict[str, Any]:
        """Create a project. Use its ID when creating epics."""
        return await run_in_request(
            container,
            lambda scope: asdict(
                scope.get(CreateProject).execute(
                    CreateProjectInput(title, prompt),
                ),
            ),
        )

    @server.tool(annotations=mutation)
    async def update_project(
        project_id: UUID,
        expected_version: int,
        title: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Edit project instructions using the current version."""
        return await run_in_request(
            container,
            lambda scope: asdict(
                scope.get(UpdateProject).execute(
                    UpdateProjectInput(
                        project_id,
                        expected_version,
                        title,
                        prompt,
                    ),
                ),
            ),
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def clear_cancelled(project_id: UUID) -> dict[str, Any]:
        """Permanently remove all cancelled tasks in this project only."""
        return await run_in_request(
            container,
            lambda scope: asdict(
                scope.get(ClearCancelled).execute(
                    ClearCancelledInput(project_id),
                ),
            ),
        )

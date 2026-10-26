import json
from pathlib import Path
from typing import Any

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent, TextResourceContents

from eonarq.shared_kernel.infrastructure.config import Config
from tests.support import running_server


async def call(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = await session.call_tool(name, arguments or {})
    assert not result.isError, result.content
    assert result.structuredContent is not None
    return result.structuredContent


def test_real_mcp_protocol_shared_api_and_restart(
    config: Config,
    tmp_path: Path,
) -> None:
    async def scenario(url: str) -> str:
        async with (
            httpx.AsyncClient(trust_env=False, timeout=15) as http,
            streamable_http_client(url + "/mcp", http_client=http) as (
                read,
                write,
                _,
            ),
            ClientSession(read, write) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "Eonarq"
            tools = {
                tool.name: tool for tool in (await session.list_tools()).tools
            }
            assert set(tools) == {
                "list_epics",
                "get_board",
                "get_task",
                "get_task_prompt",
                "create_task",
                "update_task",
                "move_task",
                "delete_task",
                "create_project",
                "update_project",
                "list_projects",
                "clear_cancelled",
            }
            assert tools["get_board"].annotations is not None
            assert tools["delete_task"].annotations is not None
            assert tools["get_board"].annotations.readOnlyHint is True
            assert tools["delete_task"].annotations.destructiveHint is True
            project = await call(
                session,
                "create_project",
                {"title": "MCP project", "prompt": "Project instructions"},
            )
            epic = await call(
                session,
                "create_task",
                {
                    "title": "MCP epic",
                    "project_id": project["project_id"],
                    "kind": "epic",
                    "prompt": "Epic instructions",
                },
            )
            master = await call(
                session,
                "create_task",
                {
                    "title": "MCP master",
                    "kind": "master",
                    "parent_id": epic["task_id"],
                    "prompt": "Master instructions",
                },
            )
            child = await call(
                session,
                "create_task",
                {
                    "title": "MCP child",
                    "kind": "subtask",
                    "parent_id": master["task_id"],
                },
            )
            other = await call(
                session,
                "create_task",
                {
                    "title": "Other master",
                    "kind": "master",
                    "parent_id": epic["task_id"],
                },
            )
            changed = await call(
                session,
                "update_task",
                {
                    "task_id": child["task_id"],
                    "expected_version": 1,
                    "prompt": "Edited via MCP",
                    "status": "done",
                    "action": "CHECK",
                },
            )
            assert changed["version"] == 2
            moved = await call(
                session,
                "move_task",
                {
                    "task_id": child["task_id"],
                    "parent_id": other["task_id"],
                    "expected_version": 2,
                },
            )
            assert moved["version"] == 3
            current = await call(
                session,
                "get_task",
                {"task_id": child["task_id"]},
            )
            assert current["prompt"] == "Edited via MCP"
            assert current["action"] == "CHECK"
            assert current["project_id"] == project["project_id"]
            assert current["parent_id"] == other["task_id"]
            epics = await call(session, "list_epics")
            assert epics["result"][0]["id"] == epic["task_id"]
            board = await call(
                session,
                "get_board",
                {"epic_id": epic["task_id"]},
            )
            assert board["total"] == 2
            assert board["done"] == 1
            assert board["flow"]["total"] == 2
            assert board["flow"]["todo"] == 2
            assert board["flow"]["wip"] == 0
            prompts = await session.list_prompts()
            assert [prompt.name for prompt in prompts.prompts] == [
                "work_on_task",
            ]
            prompt = await session.get_prompt(
                "work_on_task",
                {"task_id": child["task_id"]},
            )
            assert isinstance(prompt.messages[0].content, TextContent)
            assert "Epic instructions" in prompt.messages[0].content.text
            assert "Edited via MCP" in prompt.messages[0].content.text
            tool_prompt = await session.call_tool(
                "get_task_prompt",
                {"task_id": child["task_id"]},
            )
            assert not tool_prompt.isError
            resources = await session.list_resources()
            assert str(resources.resources[0].uri) == "eonarq://epics"
            resource = await session.read_resource(
                "eonarq://tasks/" + child["task_id"],
            )
            assert isinstance(resource.contents[0], TextResourceContents)
            assert json.loads(resource.contents[0].text)["version"] == 3
            stale = await session.call_tool(
                "update_task",
                {
                    "task_id": child["task_id"],
                    "expected_version": 1,
                    "title": "Stale",
                },
            )
            assert stale.isError
            invalid = await session.call_tool(
                "create_task",
                {
                    "title": "Bad",
                    "kind": "subtask",
                    "parent_id": epic["task_id"],
                },
            )
            assert invalid.isError
            http_task = (
                await http.get(
                    url + "/api/planning/q/tasks/" + child["task_id"],
                )
            ).json()
            assert http_task["prompt"] == "Edited via MCP"
            response = await http.post(
                url + "/api/planning/c/update",
                json={
                    "task_id": child["task_id"],
                    "expected_version": 3,
                    "prompt": "Edited via HTTP",
                },
            )
            assert response.status_code == 200
            assert (
                await call(
                    session,
                    "get_task",
                    {"task_id": child["task_id"]},
                )
            )["prompt"] == "Edited via HTTP"
            latest = await call(
                session,
                "get_task",
                {"task_id": master["task_id"]},
            )
            await call(
                session,
                "delete_task",
                {
                    "task_id": master["task_id"],
                    "expected_version": latest["version"],
                },
            )
            discarded = await call(
                session,
                "create_task",
                {
                    "title": "Discard",
                    "kind": "master",
                    "parent_id": epic["task_id"],
                    "action": "RESEARCH",
                },
            )
            discard_child = await call(
                session,
                "create_task",
                {
                    "title": "Discard child",
                    "kind": "subtask",
                    "parent_id": discarded["task_id"],
                },
            )
            discard_latest = await call(
                session,
                "get_task",
                {"task_id": discarded["task_id"]},
            )
            await call(
                session,
                "update_task",
                {
                    "task_id": discarded["task_id"],
                    "expected_version": discard_latest["version"],
                    "status": "cancelled",
                },
            )
            assert (
                await call(
                    session,
                    "get_task",
                    {"task_id": discard_child["task_id"]},
                )
            )["status"] == "cancelled"
            cleared = await call(
                session,
                "clear_cancelled",
                {"project_id": project["project_id"]},
            )
            assert cleared["deleted"] == 2
            assert (
                await call(
                    session,
                    "get_board",
                    {"project_id": project["project_id"]},
                )
            )["flow"]["cancelled"] == 0
            await call(
                session,
                "update_project",
                {
                    "project_id": project["project_id"],
                    "expected_version": 1,
                    "prompt": "Updated project context",
                },
            )
            assert (await call(session, "list_projects"))["result"][0][
                "prompt"
            ] == "Updated project context"
            return child["task_id"]

    with running_server(config.DATABASE_URL, tmp_path / "first.log") as url:
        task_id = anyio.run(scenario, url)
    with (
        running_server(config.DATABASE_URL, tmp_path / "second.log") as url,
        httpx.Client(base_url=url, trust_env=False) as http,
    ):
        task = http.get("/api/planning/q/tasks/" + task_id).json()
        assert task["prompt"] == "Edited via HTTP"
        assert task["version"] == 4
        assert task["action"] == "CHECK"
        prompt = http.get(
            "/api/planning/q/tasks/" + task_id + "/prompt",
        ).json()["content"]
        assert "Updated project context" in prompt

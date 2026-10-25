from typing import Any
from uuid import uuid7

from fastapi.testclient import TestClient


def create(
    client: TestClient,
    title: str,
    kind: str,
    parent_id: str | None = None,
    prompt: str = "",
) -> dict[str, Any]:
    response = client.post(
        "/api/planning/c/create",
        json={
            "title": title,
            "kind": kind,
            "parent_id": parent_id,
            "prompt": prompt,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def get(client: TestClient, task_id: str) -> dict[str, Any]:
    response = client.get("/api/planning/q/tasks/" + task_id)
    assert response.status_code == 200
    return response.json()


def test_shared_crud_and_inherited_prompts(client: TestClient) -> None:
    epic = create(client, "Epic", "epic", prompt="Epic instructions")
    master = create(
        client,
        "Master",
        "master",
        epic["task_id"],
        "Master instructions",
    )
    child = create(
        client,
        "Subtask",
        "subtask",
        master["task_id"],
        "Subtask instructions",
    )
    board = client.get("/api/planning/q/board").json()
    assert board["total"] == 1
    assert len(board["tasks"]) == 3
    assert board["cells"][0]["master_id"] == master["task_id"]
    response = client.post(
        "/api/planning/c/update",
        json={
            "task_id": master["task_id"],
            "expected_version": get(client, master["task_id"])["version"],
            "status": "done",
        },
    )
    assert response.status_code == 409
    changed = client.post(
        "/api/planning/c/update",
        json={
            "task_id": child["task_id"],
            "expected_version": 1,
            "prompt": "Edited in the UI",
            "status": "done",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert client.get("/api/planning/q/board").json()["percent"] == 100
    assert get(client, master["task_id"])["status"] == "todo"
    context = client.get(
        "/api/planning/q/tasks/" + child["task_id"] + "/prompt",
    ).json()["content"]
    assert "Epic instructions" in context
    assert "Master instructions" in context
    assert "Edited in the UI" in context
    stale = client.post(
        "/api/planning/c/update",
        json={
            "task_id": child["task_id"],
            "expected_version": 1,
            "prompt": "Stale",
        },
    )
    assert stale.status_code == 409
    assert get(client, child["task_id"])["prompt"] == "Edited in the UI"
    version = get(client, epic["task_id"])["version"]
    assert (
        client.post(
            "/api/planning/c/delete",
            json={"task_id": epic["task_id"], "expected_version": version},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/planning/c/delete",
            json={
                "task_id": epic["task_id"],
                "expected_version": version,
                "recursive": True,
            },
        ).status_code
        == 200
    )
    assert client.get("/api/planning/q/board").json()["tasks"] == []
    assert (
        client.get("/api/planning/q/tasks/" + child["task_id"]).status_code
        == 404
    )


def test_move_between_epics_and_scope(client: TestClient) -> None:
    first = create(client, "First", "epic")
    second = create(client, "Second", "epic")
    master = create(client, "Master", "master", first["task_id"])
    moved = client.post(
        "/api/planning/c/move",
        json={
            "task_id": master["task_id"],
            "parent_id": second["task_id"],
            "expected_version": 1,
        },
    )
    assert moved.status_code == 200
    scoped = client.get(
        "/api/planning/q/board",
        params={"epic_id": second["task_id"]},
    ).json()
    assert {task["id"] for task in scoped["tasks"]} == {
        second["task_id"],
        master["task_id"],
    }
    assert (
        client.get(
            "/api/planning/q/board",
            params={"epic_id": master["task_id"]},
        ).status_code
        == 400
    )


def test_transport_and_domain_rejections(client: TestClient) -> None:
    assert (
        client.post(
            "/api/planning/c/create",
            json={"title": " ", "kind": "epic"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={"title": "Task", "kind": "wrong"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={"title": "Task", "kind": "master"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={
                "title": "Task",
                "kind": "master",
                "parent_id": str(uuid7()),
            },
        ).status_code
        == 404
    )
    assert client.get("/api/planning/q/tasks/invalid").status_code == 422
    assert (
        client.get("/api/planning/q/tasks/" + str(uuid7())).status_code == 404
    )
    assert (
        client.get(
            "/api/planning/q/board",
            params={"epic_id": str(uuid7())},
        ).status_code
        == 404
    )


def test_local_shell_schema_and_origin_boundary(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    shell = client.get("/")
    assert shell.status_code == 200
    assert 'id="task-prompt"' in shell.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200
    assert (
        "/api/planning/c/create" in client.get("/openapi.json").json()["paths"]
    )
    assert (
        client.get("/health", headers={"host": "evil.example"}).status_code
        == 400
    )
    payload = {"title": "Cross-origin", "kind": "epic"}
    assert (
        client.post(
            "/api/planning/c/create",
            json=payload,
            headers={"origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json=payload,
            headers={"origin": "http://127.0.0.1"},
        ).status_code
        == 201
    )

from fastapi.testclient import TestClient

from tests.integrations.test_http import create, get


def test_report_completion_patch_clear_and_conflicts(
    client: TestClient,
) -> None:
    epic = create(client, "Epic", "epic", prompt="Instructions")
    task_id = epic["task_id"]
    assert get(client, task_id)["report"] == ""
    report = "  # Results\nВыполнено; tests passed.\n"
    completed = client.post(
        "/api/planning/c/update",
        json={
            "task_id": task_id,
            "expected_version": 1,
            "status": "done",
            "report": report,
        },
    )
    assert completed.status_code == 200
    task = get(client, task_id)
    assert (task["report"], task["status"], task["prompt"]) == (
        report,
        "done",
        "Instructions",
    )
    stale = client.post(
        "/api/planning/c/update",
        json={"task_id": task_id, "expected_version": 1, "report": "Stale"},
    )
    assert stale.status_code == 409
    patched = client.post(
        "/api/planning/c/update",
        json={"task_id": task_id, "expected_version": 2, "title": "Renamed"},
    )
    assert patched.status_code == 200
    assert get(client, task_id)["report"] == report
    invalid = client.post(
        "/api/planning/c/update",
        json={
            "task_id": task_id,
            "expected_version": 3,
            "report": "x" * 200001,
        },
    )
    assert invalid.status_code == 400
    assert get(client, task_id)["version"] == 3
    cleared = client.post(
        "/api/planning/c/update",
        json={"task_id": task_id, "expected_version": 3, "report": ""},
    )
    assert cleared.status_code == 200
    assert get(client, task_id)["report"] == ""


def test_validate_action_contract_rejects_old_name(client: TestClient) -> None:
    project_id = client.get("/api/planning/q/projects").json()[0]["id"]
    response = client.post(
        "/api/planning/c/create",
        json={
            "title": "Validate",
            "kind": "epic",
            "project_id": project_id,
            "action": "VALIDATE",
        },
    )
    assert response.status_code == 201
    task_id = response.json()["task_id"]
    assert get(client, task_id)["action"] == "VALIDATE"
    rejected = client.post(
        "/api/planning/c/update",
        json={"task_id": task_id, "expected_version": 1, "action": "CHECK"},
    )
    assert rejected.status_code == 422
    assert get(client, task_id)["version"] == 1
    schema = client.get("/openapi.json").json()
    assert schema["components"]["schemas"]["TaskAction"]["enum"] == [
        "RESEARCH",
        "ACTION",
        "VALIDATE",
    ]


def test_project_isolation_actions_cancellation_and_clear(
    client: TestClient,
) -> None:
    original = client.get("/api/planning/q/projects").json()[0]
    epic = create(client, "Epic", "epic")
    master = create(client, "Master", "master", epic["task_id"])
    child = create(client, "Child", "subtask", master["task_id"])
    other = client.post(
        "/api/planning/c/projects/create",
        json={"title": "Other", "prompt": "Shared instructions"},
    ).json()["project_id"]
    other_epic = client.post(
        "/api/planning/c/create",
        json={
            "title": "Other epic",
            "kind": "epic",
            "project_id": other,
            "action": "RESEARCH",
        },
    ).json()["task_id"]
    assert (
        client.get(
            "/api/planning/q/board",
            params={"project_id": original["id"]},
        ).json()["flow"]["total"]
        == 3
    )
    board = client.get(
        "/api/planning/q/board",
        params={"project_id": other},
    ).json()
    assert [task["id"] for task in board["tasks"]] == [other_epic]
    assert board["tasks"][0]["action"] == "RESEARCH"
    assert (
        client.get(
            "/api/planning/q/board",
            params={"project_id": other, "epic_id": epic["task_id"]},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/planning/c/move",
            json={
                "task_id": master["task_id"],
                "parent_id": other_epic,
                "expected_version": get(client, master["task_id"])["version"],
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={
                "title": "Wrong project",
                "kind": "subtask",
                "parent_id": master["task_id"],
                "project_id": other,
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/planning/c/update",
            json={
                "task_id": child["task_id"],
                "expected_version": 1,
                "action": "VALIDATE",
            },
        ).status_code
        == 200
    )
    response = client.post(
        "/api/planning/c/update",
        json={
            "task_id": master["task_id"],
            "expected_version": get(client, master["task_id"])["version"],
            "status": "cancelled",
        },
    )
    assert response.status_code == 200
    assert get(client, child["task_id"])["status"] == "cancelled"
    assert get(client, child["task_id"])["action"] == "VALIDATE"
    result = client.post(
        "/api/planning/c/clear-cancelled",
        json={"project_id": original["id"]},
    )
    assert result.status_code == 200
    assert result.json() == {"deleted": 2}
    assert get(client, other_epic)["status"] == "todo"
    assert get(client, epic["task_id"])["status"] == "todo"
    response = client.post(
        "/api/planning/c/projects/update",
        json={
            "project_id": other,
            "expected_version": 1,
            "title": "Renamed",
            "prompt": "Updated instructions",
        },
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/api/planning/c/projects/update",
            json={
                "project_id": other,
                "expected_version": 1,
                "prompt": "Stale",
            },
        ).status_code
        == 409
    )
    assert (
        "Updated instructions"
        in client.get(
            "/api/planning/q/tasks/" + other_epic + "/prompt",
        ).json()["content"]
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={"title": "No project", "kind": "epic"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/planning/c/create",
            json={
                "title": "Bad action",
                "kind": "epic",
                "project_id": other,
                "action": "BAD",
            },
        ).status_code
        == 422
    )

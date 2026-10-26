import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect, sync_playwright

from tests.support import running_server


@pytest.fixture
def page(tmp_path: Path) -> Iterator[Page]:
    database = "sqlite:///" + str(tmp_path / "browser.sqlite3")
    with (
        running_server(database, tmp_path / "browser.log") as url,
        sync_playwright() as playwright,
    ):
        browser = playwright.chromium.launch(
            channel=os.getenv("EONARQ_BROWSER_CHANNEL"),
            headless=True,
        )
        context = browser.new_context(
            base_url=url,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        try:
            page.goto(url)
            expect(page.locator("#task-list")).to_contain_text(
                "Create your first project",
            )
            page.request.post(
                "/api/planning/c/projects/create",
                data={"title": "Test project"},
            )
            page.locator("#refresh").click()
            expect(page.locator("#task-list")).to_contain_text(
                "Create your first epic",
            )
            yield page
        finally:
            context.close()
            browser.close()


def save_form(page: Page, title: str, prompt: str) -> None:
    page.locator("#task-title").fill(title)
    page.locator("#task-prompt").fill(prompt)
    page.locator("#save-task").click()
    expect(page.locator("#task-dialog")).not_to_be_visible()


def create(
    page: Page,
    title: str,
    kind: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    response = page.request.post(
        "/api/planning/c/create",
        data={
            "title": title,
            "kind": kind,
            "parent_id": parent_id,
            "project_id": page.locator("#project-select").input_value(),
        },
    )
    assert response.status == 201
    return response.json()


def test_editable_prompts_and_explicit_completion(page: Page) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def delayed_board(route: Route) -> None:
        response = route.fetch()
        time.sleep(0.2)
        route.fulfill(response=response)

    page.route("**/api/planning/q/board", delayed_board)
    page.locator("#add-task").click()
    save_form(page, "Directory compatibility", "# Epic\nKeep the context")
    expect(page.locator("h1")).to_have_text("Directory compatibility")
    page.locator("#add-task").click()
    save_form(page, "Implement API", "# Master\nAcceptance criteria")
    page.get_by_role("button", name="+ Subtask", exact=True).click()
    raw_prompt = "# Subtask\n<script>window.eonarqInjected = true</script>"
    save_form(page, "Wire the endpoint", raw_prompt)
    expect(page.locator("#waffle > .cell")).to_have_count(1)
    page.get_by_label("Mark Implement API as done", exact=True).check()
    expect(page.locator("#toast")).to_contain_text("Complete every child")
    expect(
        page.get_by_label("Mark Implement API as done", exact=True),
    ).not_to_be_checked()
    page.get_by_label("Mark Wire the endpoint as done", exact=True).check()
    expect(page.locator("#metric-percent")).to_have_text("100%")
    page.get_by_label("Mark Implement API as done", exact=True).check()
    expect(page.locator("#metric-masters")).to_have_text("1 / 1")
    page.get_by_role(
        "button",
        name="Edit Wire the endpoint",
        exact=True,
    ).click()
    expect(page.locator("#task-prompt")).to_have_value(raw_prompt)
    page.locator("#task-prompt").fill("Revised user prompt")
    page.locator("#save-task").click()
    expect(page.locator("#task-dialog")).not_to_be_visible()
    page.reload()
    page.get_by_role(
        "button",
        name="Edit Wire the endpoint",
        exact=True,
    ).click()
    expect(page.locator("#task-prompt")).to_have_value("Revised user prompt")
    assert page.evaluate("window.eonarqInjected") is None
    assert not errors


def test_flat_hover_contours_responsive_layout_and_safe_titles(
    page: Page,
) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    epic = create(page, "Compatibility", "epic")["task_id"]
    other_epic = create(page, "Second epic", "epic")["task_id"]
    first = create(page, "Master one", "master", epic)["task_id"]
    second = create(page, "Master two", "master", epic)["task_id"]
    for index in range(53):
        create(page, f"Step {index}", "subtask", first)
    for index in range(9):
        create(page, f"Other {index}", "subtask", second)
    unsafe_title = '<img src=x onerror="window.eonarqInjected=true">'
    create(page, unsafe_title, "master", other_epic)
    page.locator("#refresh").click()
    expect(page.locator(".kanban-card")).to_have_count(67)
    expect(page.locator(".kanban-column")).to_have_count(5)
    expect(page.locator("#epic-chart")).not_to_be_visible()
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth",
        )
    page.locator(".epic-card .title-button").filter(
        has_text="Compatibility",
    ).click()
    expect(page.locator("#waffle > .cell")).to_have_count(62)
    expect(page.locator("#epic-chart")).to_be_visible()
    expect(page.locator("#waffle > .task-boundaries > path")).to_have_count(2)
    first_cell = page.locator('.cell[data-group="' + first + '"]').first
    first_cell.hover()
    expect(page.locator(".task-boundary.active")).to_have_attribute(
        "data-group",
        first,
    )
    assert "Q" in (
        page.locator(".task-boundary.active").get_attribute("d") or ""
    )
    page.locator('.cell[data-group="' + second + '"]').first.hover()
    expect(page.locator(".task-boundary.active")).to_have_count(1)
    expect(page.locator(".task-boundary.active")).to_have_attribute(
        "data-group",
        second,
    )
    page.locator("h1").hover()
    expect(page.locator(".task-boundary.active")).to_have_count(0)
    out = Path(".misc/browser")
    out.mkdir(parents=True, exist_ok=True)
    first_cell.hover()
    page.screenshot(path=str(out / "workspace.png"), full_page=True)
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 1000})
        layout = page.evaluate("""() => ({
            width: innerWidth,
            scroll: document.documentElement.scrollWidth,
            overflowing: [...document.querySelectorAll('body *')]
                .filter(e => e.getBoundingClientRect().right > innerWidth + 1)
                .slice(0, 12).map(e => e.tagName + '.' + e.className)
        })""")
        assert layout["scroll"] <= width, layout
        first_cell.hover()
        expect(page.locator(".task-boundary.active")).to_have_attribute(
            "data-group",
            first,
        )
    page.set_viewport_size({"width": 390, "height": 1000})
    page.screenshot(path=str(out / "workspace-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.emulate_media(color_scheme="dark")
    page.screenshot(path=str(out / "workspace-dark.png"), full_page=True)
    page.locator("#overview").click()
    page.locator(".epic-card .title-button").filter(
        has_text="Second epic",
    ).click()
    expect(page.locator("#task-list")).to_contain_text(unsafe_title)
    assert page.locator("#task-list img").count() == 0
    assert page.evaluate("window.eonarqInjected") is None
    assert not errors


def set_status(page: Page, task_id: str, status: str) -> None:
    task = page.request.get("/api/planning/q/tasks/" + task_id).json()
    response = page.request.post(
        "/api/planning/c/update",
        data={
            "task_id": task_id,
            "expected_version": task["version"],
            "status": status,
        },
    )
    assert response.status == 200, response.text()


def test_agile_drag_keyboard_metrics_and_epic_navigation(page: Page) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    first = create(page, "Plan interface", "epic")["task_id"]
    active = create(page, "Implement flow", "epic")["task_id"]
    blocked = create(page, "Waiting on review", "epic")["task_id"]
    done = create(page, "Released", "epic")["task_id"]
    guarded = create(page, "Open work", "epic")["task_id"]
    master = create(page, "Open master", "master", guarded)["task_id"]
    set_status(page, active, "in_progress")
    set_status(page, blocked, "blocked")
    set_status(page, done, "done")
    page.locator("#refresh").click()
    expect(page.locator(".kanban-card")).to_have_count(6)
    expect(page.locator("#metric-masters")).to_have_text("1 / 6")
    expect(page.locator("#metric-wip")).to_have_text("2")
    expect(page.locator("#metric-blocked")).to_have_text("1")
    expect(page.locator("#metric-percent")).to_have_text("20%")
    expect(page.locator("#metric-closed-label")).to_have_text("tasks closed")

    def card(task_id: str, status: str) -> str:
        return (
            '.kanban-column[data-status="' + status + '"] '
            '.kanban-card[data-task="' + task_id + '"]'
        )

    page.locator(card(first, "todo") + " .drag-handle").drag_to(
        page.locator(
            '.kanban-column[data-status="in_progress"] .kanban-cards',
        ),
    )
    expect(page.locator(card(first, "in_progress"))).to_be_visible()
    expect(page.locator("#metric-wip")).to_have_text("3")
    status_menu = page.get_by_label("Status for Implement flow", exact=True)
    status_menu.focus()
    status_menu.press("End")
    expect(page.locator(card(active, "cancelled"))).to_be_visible()
    status_menu.press("ArrowUp")
    expect(page.locator(card(active, "done"))).to_be_visible()
    expect(page.locator("#metric-masters")).to_have_text("2 / 6")
    expect(page.locator("#metric-percent")).to_have_text("40%")
    expect(page.locator("#metric-wip")).to_have_text("2")
    page.locator(card(guarded, "todo") + " .drag-handle").drag_to(
        page.locator('.kanban-column[data-status="done"] .kanban-cards'),
    )
    expect(page.locator("#toast")).to_contain_text("Complete every child")
    expect(page.locator(card(guarded, "todo"))).to_be_visible()
    expect(page.locator(card(guarded, "done"))).to_have_count(0)
    expect(page.locator("#metric-masters")).to_have_text("2 / 6")
    page.get_by_label("Status for Plan interface", exact=True).select_option(
        "blocked",
    )
    expect(page.locator(card(first, "blocked"))).to_be_visible()
    expect(page.locator("#metric-blocked")).to_have_text("2")
    page.reload()
    expect(page.locator(card(first, "blocked"))).to_be_visible()
    expect(page.locator(card(active, "done"))).to_be_visible()
    set_status(page, active, "todo")
    expect(page.locator(card(active, "todo"))).to_be_visible(timeout=10000)
    expect(page.locator("#metric-masters")).to_have_text("1 / 6")
    page.locator(card(guarded, "todo") + " .title-button").click()
    expect(page.locator("#epic-chart")).to_be_visible()
    expect(page.locator(".kanban-column")).to_have_count(0)
    expect(page.locator("#waffle > .cell")).to_have_count(1)
    expect(page.locator("#metric-masters")).to_have_text("0 / 1")
    set_status(page, master, "blocked")
    page.locator("#refresh").click()
    expect(page.locator("#metric-wip")).to_have_text("1")
    expect(page.locator("#metric-blocked")).to_have_text("1")
    expect(page.locator("#metric-blocked-label")).to_have_text(
        "blocked master tasks",
    )
    page.locator("#overview").click()
    expect(page.locator("#epic-chart")).not_to_be_visible()
    expect(page.locator("#metric-blocked")).to_have_text("3")
    out = Path(".misc/browser")
    out.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out / "agile-board.png"), full_page=True)
    page.emulate_media(color_scheme="dark")
    page.screenshot(
        path=str(out / "agile-board-dark.png"),
        full_page=True,
        animations="disabled",
    )
    browser = page.context.browser
    assert browser is not None
    mobile_context = browser.new_context(
        viewport={"width": 390, "height": 900},
        is_mobile=True,
        has_touch=True,
    )
    try:
        mobile = mobile_context.new_page()
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto(page.url)
        expect(mobile.locator(".kanban-card")).to_have_count(6)
        mobile.get_by_label(
            "Status for Implement flow",
            exact=True,
        ).select_option("in_progress")
        expect(mobile.locator(card(active, "in_progress"))).to_be_visible()
        expect(mobile.locator("#metric-wip")).to_have_text("4")
        assert mobile.evaluate(
            "document.documentElement.scrollWidth <= innerWidth",
        )
        mobile.screenshot(
            path=str(out / "agile-board-mobile.png"),
            full_page=True,
        )
        mobile.locator(card(guarded, "todo") + " .title-button").click()
        expect(mobile.locator("#epic-chart")).to_be_visible()
        expect(mobile.locator("#waffle > .cell")).to_have_count(1)
        mobile.locator("#overview").click()
        expect(mobile.locator(".kanban-column")).to_have_count(5)
    finally:
        mobile_context.close()
    assert not errors

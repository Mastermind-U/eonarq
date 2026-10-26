from playwright.sync_api import Page, expect

from tests.browser.test_workspace import create, page as page, save_form


def test_projects_grouping_actions_and_clear(page: Page) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    first_project = page.locator("#project-select").input_value()
    epic = create(page, "First epic", "epic")["task_id"]
    master = create(page, "First master", "master", epic)["task_id"]
    child = create(page, "Check result", "subtask", master)["task_id"]
    create(page, "Second epic", "epic")
    page.locator("#refresh").click()
    expect(page.locator(".kanban-card")).to_have_count(4)
    expect(page.locator(".kanban-column")).to_have_count(5)
    page.get_by_label("Group by epic").check()
    expect(page.locator(".kanban-board")).to_have_count(2)
    expect(page.locator(".kanban-card")).to_have_count(4)
    page.reload()
    expect(page.get_by_label("Group by epic")).to_be_checked()
    page.locator('.kanban-card[data-task="' + child + '"] .task-edit').click()
    page.locator("#task-action").select_option("VALIDATE")
    save_form(page, "Check result", "Check instructions")
    expect(
        page.locator('.kanban-card[data-task="' + child + '"] .action-badge'),
    ).to_have_text("VALIDATE")
    page.locator("#new-project").click()
    page.locator("#project-title").fill("Other project")
    page.locator("#project-prompt").fill("Other instructions")
    page.locator("#save-project").click()
    expect(page.locator("#project-dialog")).not_to_be_visible()
    expect(page.locator("h1")).to_have_text("Other project")
    expect(page.locator(".kanban-card")).to_have_count(0)
    other_epic = create(page, "Other work", "epic")["task_id"]
    page.locator("#project-select").select_option(first_project)
    expect(page.locator(".kanban-card")).to_have_count(4)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_label("Status for First master", exact=True).select_option(
        "cancelled",
    )
    expect(
        page.locator('.kanban-column[data-status="cancelled"] .kanban-card'),
    ).to_have_count(2)
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#clear-cancelled").click()
    expect(page.locator(".kanban-card")).to_have_count(2)
    expect(page.locator("#clear-cancelled")).not_to_be_visible()
    page.locator("#project-select").select_option(label="Other project")
    expect(
        page.locator('.kanban-card[data-task="' + other_epic + '"]'),
    ).to_have_count(1)
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth",
        )
    assert not errors

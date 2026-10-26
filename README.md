# Eonarq

A local tracker for long-running epics, editable prompts and coding agents.

```text
Project
  └─ Epic
       └─ Master task
            └─ Subtask
```

The web interface and MCP tools share one SQLite database and the same application use cases. No account or authentication is required. The default published address is loopback only.

- Create, edit, reorder, move and delete tasks through MCP or the HTTP API.
- Create, edit, complete and delete tasks in the web interface. Edit Markdown prompts at every level and save completion results in a separate `report` field.
- Select a project from the dropdown above Epics; use its + button to create one. Projects have editable shared prompts.
- The project board shows every epic, master task and subtask in To do, In progress, Blocked, Done and Cancelled columns. Enable Group by epic for separate lanes. Drag a card or use its status menu with a keyboard or touch screen.
- Every task has an Action: `RESEARCH`, `ACTION` (default), or `VALIDATE`. Edit it alongside the task prompt.
- Open an epic to see its progress diagram, master tasks and subtasks. Progress is one compact field of squares; hover or focus a square to outline its master task. Click a square to edit its task and prompt. Green squares are done, yellow squares are WIP (in progress or blocked), red squares are cancelled, and hollow squares are to do.
- Metrics show leaf-task progress, closed epics/master tasks, work in progress and blocked work. The project board counts all task levels; an epic page counts its direct master tasks. WIP includes both in-progress and blocked cards.
- MCP can load the selected prompt together with its current project/epic/master context. Changes made in the browser are immediately available to agents; the browser refreshes external changes every five seconds while the editor is closed.

## Run with Docker (recommended)

Install Docker and start the published image; a source checkout and Python installation are not required:

```sh
docker pull ghcr.io/mastermind-u/eonarq:latest
docker run -d --name eonarq --init --restart unless-stopped --stop-timeout 20 -p 127.0.0.1:8765:8765 -v eonarq_data:/data ghcr.io/mastermind-u/eonarq:latest
docker ps --filter name=eonarq
```

These commands work in PowerShell and POSIX shells.

Open **http://127.0.0.1:8765**.

| Endpoint | URL |
| --- | --- |
| Web interface | `http://127.0.0.1:8765/` |
| Streamable HTTP MCP | `http://127.0.0.1:8765/mcp` |
| Interactive HTTP API | `http://127.0.0.1:8765/docs` |
| Health | `http://127.0.0.1:8765/health` |

Migrations run before the server starts. This pre-release schema is kept in a single initial revision; an existing database already stamped `0001_initial` needs an explicit SQL upgrade before running a changed schema. Back it up first; pulling a new image alone does not alter that database. Data lives in the `eonarq_data` named volume at `/data/eonarq.sqlite3`. Stopping or removing the container preserves this named volume; reuse it when recreating the container.

```sh
docker logs -f eonarq
docker restart eonarq
docker stop eonarq
```

To change the host port, use `-p 127.0.0.1:8766:8765` when creating the container and update the MCP client URL. The container continues to listen on port 8765.

If switching an existing Compose installation, reuse its data volume. Find the volume name with `docker inspect eonarq-eonarq-1 --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}'`, then stop that container with `docker stop eonarq-eonarq-1`. Replace `eonarq_data` in the launch command with the printed name (usually `eonarq_eonarq_data`) to keep the existing database.

### Update the service

Pull the new image and recreate the container with the same data volume and port:

```sh
docker pull ghcr.io/mastermind-u/eonarq:latest
docker stop eonarq
docker rm eonarq
docker run -d --name eonarq --init --restart unless-stopped --stop-timeout 20 -p 127.0.0.1:8765:8765 -v eonarq_data:/data ghcr.io/mastermind-u/eonarq:latest
```

Use the same volume name chosen at installation, including when switching from Compose. Replace `latest` in both commands with a release tag such as `0.1.0` or a published `sha-…` tag to pin the image. CI builds and publishes the image. If the GHCR package is private, log in with `docker login ghcr.io` before pulling; make the package public in GitHub package settings for anonymous pulls.

### Back up the database

Create a consistent snapshot with SQLite's Backup API while the application keeps running, then copy the snapshot to the host with `docker cp`. The image already includes Python and its `sqlite3` module:

```sh
docker exec eonarq python -c "import sqlite3; source = sqlite3.connect('file:/data/eonarq.sqlite3?mode=ro', uri=True); target = sqlite3.connect('/tmp/eonarq-backup.sqlite3'); source.backup(target, pages=256, sleep=0.1); target.close(); source.close()"
docker cp eonarq:/tmp/eonarq-backup.sqlite3 ./backup.sqlite3
```

The self-contained backup, including committed WAL changes, is now at `./backup.sqlite3` on the host. Use a different host filename for each backup. With Compose, replace `eonarq` in these commands with the container name shown by `docker compose ps -a` (usually `eonarq-eonarq-1`).

### Docker Compose (optional)

Compose v2 is an alternative to the `docker run` command above. Download the main Compose file and start the published image:

```sh
mkdir eonarq
cd eonarq
curl --fail --location --output docker-compose.yml https://raw.githubusercontent.com/Mastermind-U/eonarq/main/docker-compose.yml
docker compose pull
docker compose up -d
docker compose ps
```

In Windows PowerShell, use `curl.exe` instead of `curl` if `curl` resolves to `Invoke-WebRequest`.

Update from the same directory:

```sh
curl --fail --location --output docker-compose.yml https://raw.githubusercontent.com/Mastermind-U/eonarq/main/docker-compose.yml
docker compose pull
docker compose up -d
```

Use `docker compose logs -f eonarq`, `docker compose restart eonarq` and `docker compose down` to manage the service. Compose keeps data in its project-prefixed named volume (usually `eonarq_eonarq_data`), which differs from the `docker run` example's `eonarq_data`. Keep the same Compose directory/project when updating; `down` preserves the volume and `down -v` deletes it. The backup commands above also work with the Compose container's name.

Set `EONARQ_PORT=8766` or `EONARQ_TAG=<published tag>` in a local `.env` file to change the host port or pin the image, then run `docker compose up -d` and update the MCP URL if the port changed.

## Connect Codex

Start Eonarq with Docker or the native command below. It exposes MCP over **Streamable HTTP** at **`http://127.0.0.1:8765/mcp`**.

### Configure through settings

1. Open **Settings → MCP servers → Add server** (in the IDE extension, open the gear menu and select **MCP servers**).
2. Name the server `eonarq` and select **Streamable HTTP**.
3. Set the URL to `http://127.0.0.1:8765/mcp`. Include `/mcp`; the root address serves the web interface.
4. Leave command, arguments and authentication fields unset. Eonarq connects to the already-running service and requires no token.
5. Save, then select **Restart** in the desktop app or **Restart extension** in the IDE extension. Check `/mcp` after restarting.

If you previously added a server such as `http-localhost-8765` with `command = "eonarq"` and `args = [""]`, replace that entry with the HTTP connection. `command` and `args` configure a **STDIO** server; Eonarq's CLI starts the web service and does not implement STDIO MCP. A URL-like server name alone does not configure an HTTP connection.

### Configure through the CLI or config.toml

Add the same HTTP endpoint with the Codex CLI:

```sh
codex mcp add eonarq --url http://127.0.0.1:8765/mcp
codex mcp get eonarq
codex mcp list
```

Alternatively, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.eonarq]
url = "http://127.0.0.1:8765/mcp"
enabled = true
```

Start a new Codex session and check `/mcp`. Configuration is shared by the Codex CLI and IDE extension. See [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp/) and the [HTTP registration example](https://developers.openai.com/resources/docs-mcp).

## Connect Claude Code

```sh
claude mcp add --transport http --scope user eonarq http://127.0.0.1:8765/mcp
claude mcp get eonarq
claude mcp list
```

Start a new Claude Code session and check `/mcp`. For project-local configuration, use `--scope project` instead of `--scope user`, or add this `.mcp.json` to the project where the agent works:

```json
{
  "mcpServers": {
    "eonarq": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

See the [official Claude Code MCP guide](https://code.claude.com/docs/en/mcp). These instructions are for Claude Code; they do not configure the Claude Desktop application.

Both clients connect to the running service. They do not start another copy or another database. No API keys, OAuth configuration or authorization headers are needed.

### Suggested agent instructions

Add to the working project's `AGENTS.md` or `CLAUDE.md`:

```text
Use Eonarq to track this project's work.
1. Read list_projects, then list_epics/get_board with project_id before changing the plan.
2. Read get_task and work_on_task for the selected task's latest prompt/context.
3. Keep the epic -> master -> subtask hierarchy.
4. Mark work in_progress before implementing, then save the outcome and checks in report and mark done after its checks pass (one update_task call can set both).
5. Read the current version before each update, move or delete.
6. Close a master task or epic explicitly after its children are complete.
7. Keep prompts and acceptance criteria editable by the user.
```

## Run natively

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.14+, then run from the repository root:

```sh
uv sync --locked
uv run eonarq
```

The native database defaults to `./data/eonarq.sqlite3`. Migrations run automatically. To migrate without serving, or select another database/port:

```sh
uv run eonarq --init-db
uv run eonarq --database sqlite:///./data/another.sqlite3 --port 8766
```

`python -m eonarq` is also supported. Keep the same database path and port when restarting. Native and Docker defaults use different storage locations.

| Environment variable | Native default | Meaning |
| --- | --- | --- |
| `EONARQ_DATABASE_URL` | `sqlite:///./data/eonarq.sqlite3` | Standard synchronous SQLite URL |
| `EONARQ_HOST` | `127.0.0.1` | Listener binding |
| `EONARQ_PORT` | `8765` | Listener port; Docker host publishing uses `-p` |
| `EONARQ_ALLOWED_HOSTS` | `localhost;127.0.0.1;[::1]` | Semicolon-separated permitted Host values |
| `EONARQ_BROWSER_CHANNEL` | unset | Test-only Playwright channel, e.g. `msedge` |

Native environment example in PowerShell:

```powershell
$env:EONARQ_PORT = "8766"
$env:EONARQ_DATABASE_URL = "sqlite:///./data/another.sqlite3"
uv run eonarq
```

## Task and progress rules

- Projects contain a three-level task hierarchy: epic → master → subtask. Supply `project_id` when creating an epic; children inherit their parent’s project. Moves within a project preserve IDs and descendants; cross-project moves are rejected.
- States: `todo`, `in_progress`, `blocked`, `done`, `cancelled`. Actions: `RESEARCH`, `ACTION`, `VALIDATE`.
- Cancelling a parent cancels its entire subtree, including completed descendants. Reopening any descendant reopens cancelled ancestors as `in_progress`. Clear cancelled permanently deletes cancelled branches in the selected project; it preserves other projects. The browser asks before cancelling a branch or clearing tasks. Cancelled leaves remain visible until cleared and do not contribute to progress percentages.
- A square represents a leaf: a subtask, or a master/epic that has no children. Each leaf has equal weight; progress measures completed leaves, not effort.
- Closing the last child does not automatically close its parent. A parent can be marked done only when every immediate child is done or cancelled.
- Board moves use the same version checks and completion rules as HTTP/MCP commands. A rejected move keeps the card in its saved column and shows the reason.
- Adding an open child or reopening/moving an open descendant reopens completed ancestors as `in_progress`.
- Mutations require the current `expected_version`. A stale edit returns HTTP 409 or an MCP tool error, without overwriting newer data. On conflict, reload the task and reapply the intended change.
- Order is a nonnegative integer, then stable UUID order. Titles contain 1–200 characters; prompts contain up to 200,000 characters.
- Deletion with children requires `recursive=true`. The UI requests confirmation and applies recursive deletion explicitly.

## MCP surface

| Tool | Purpose |
| --- | --- |
| `list_projects` | Project IDs, titles, shared prompts and versions |
| `create_project(title, prompt?)` | Create a project |
| `update_project(project_id, expected_version, title?, prompt?)` | Edit project instructions |
| `list_epics(project_id?)` | Epic summaries and progress |
| `get_board(epic_id?, project_id?)` | Task hierarchy, versions, progress squares and flow metrics |
| `get_task(task_id)` | Full task with editable prompt, completion report and current version |
| `get_task_prompt(task_id)` | Inherited project/epic/master/subtask context |
| `create_task(title, kind, parent_id?, prompt?, position?, project_id?, action?, report?)` | Create work at the correct level |
| `update_task(task_id, expected_version, title?, prompt?, status?, position?, action?, report?)` | Edit selected fields; omitted fields stay unchanged |
| `move_task(task_id, parent_id, expected_version)` | Move a master or subtask |
| `delete_task(task_id, expected_version, recursive?)` | Explicit deletion |
| `clear_cancelled(project_id)` | Permanently delete this project’s cancelled branches |

MCP prompt: `work_on_task(task_id)`. Resources: `eonarq://epics`, `eonarq://tasks/{task_id}`. The prompt/resource reads current stored content on every call. Read tools advertise read-only annotations; deletion advertises destructive behavior.

Example: call `create_project` with `{"title":"ToDo app"}`, then `create_task` with `{"title":"Make ToDo app","kind":"epic","project_id":"<returned project_id>","action":"RESEARCH","prompt":"Goal and acceptance criteria"}`. Use its returned `task_id` as the parent when creating a `master`, then the master's ID when creating a `subtask`.

### Completion reports

Every task has a text `report` (empty by default, up to 200,000 characters). Use it for the completed work, verification results, evidence links and remaining limitations. The task editor exposes it as **Completion report**; `get_task` and the task resource return it alongside the prompt. Reports stay editable at every status. Prompts and inherited instructions retain their own field.

Save the report and completion status atomically with `update_task`:

```json
{
  "task_id": "<task UUID>",
  "expected_version": 3,
  "status": "done",
  "report": "Implemented the endpoint. Unit and integration checks passed.\nRemaining: external acceptance."
}
```

Omitting `report` preserves its value; `report: ""` clears it. Stale versions and failed completion checks leave both the report and status unchanged.

## HTTP API

All payloads/responses and validation schemas are in `/docs`.

Board responses include `flow` counters (`total`, `todo`, `in_progress`, `blocked`, `done`, `cancelled`, `wip`, `completion_percent`). Use `project_id` to scope tasks and flow counters to a project. `epic_id` additionally scopes the tree to one epic and the flow counters to its master tasks. Without either filter, the response covers all projects and summarizes their epics. Each task also exposes `flow` for its immediate children. These counters describe explicit task statuses; leaf completion remains a separate progress measure.

| Method | Path | Input |
| --- | --- | --- |
| GET | `/api/planning/q/projects` | List projects with their editable prompts |
| GET | `/api/planning/q/board` | Optional `project_id` and `epic_id` query parameters |
| POST | `/api/planning/c/projects/create` | `title`, optional `prompt` |
| POST | `/api/planning/c/projects/update` | `project_id`, `expected_version`, optional `title`, `prompt` |
| POST | `/api/planning/c/clear-cancelled` | `project_id` |
| GET | `/api/planning/q/tasks/{id}` | UUID path parameter |
| GET | `/api/planning/q/tasks/{id}/prompt` | UUID path parameter |
| POST | `/api/planning/c/create` | `title`, `kind`, `project_id` for epics; optional `parent_id`, `prompt`, `position`, `action`, `report` |
| POST | `/api/planning/c/update` | `task_id`, `expected_version`, optional editable fields |
| POST | `/api/planning/c/move` | `task_id`, `parent_id`, `expected_version` |
| POST | `/api/planning/c/delete` | `task_id`, `expected_version`, optional `recursive` |

Domain validation returns 400, missing tasks 404, conflicts 409, malformed transport input 422. Browser writes must be same-origin. MCP clients may omit Origin. No permissive CORS policy is installed.

## Architecture and development

Stack: uv, Python 3.14, synchronous FastAPI routes, synchronous Dishka scopes, synchronous SQLAlchemy with the standard SQLite driver, Jinja templates and browser JavaScript. MCP's ASGI transport is asynchronous; each tool offloads synchronous application work to a thread with its own request scope/session.

`planning` is a DDD/CQRS context. Command and query entities/mappings are separate; framework-free use cases share domain rules. SQL uses Tables, native imperative mappings and explicit shared `EntitySaver`/`TransactionManager` ports. SQLite uses WAL, foreign keys, explicit read transactions and `BEGIN IMMEDIATE` before command reads. Rollback restores tracked entity values/identities. Query entities reject ORM writes.

See [AGENTS.md](AGENTS.md) for dependency rules, validation and testing conventions used in this project. No native compilation or executable bundling is involved.

```sh
uv sync --locked
uv run lint-imports
uv run pytest tests/units
uv run pytest tests/integrations
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
git diff --check
```

Browser checks (real HTTP application, prompt editing, completion rules, XSS-safe text, contours and responsive layout):

```sh
uv run playwright install chromium
uv run pytest tests/browser -n 0
```

On Windows with Edge installed, `$env:EONARQ_BROWSER_CHANNEL = "msedge"` can be used instead of downloading Chromium. Screenshots are written to `.misc/browser/`.

Unit and integration tests run on the host. Integration tests use private temporary SQLite databases and a real native HTTP server for the MCP SDK client; they cover rollback, concurrent writers, API/MCP consistency and restart persistence.

### CI and GHCR publication

`.github/workflows/ci.yml` keeps unit/integration jobs separate on Linux and Windows, runs import-linter, Ruff, mypy and browser checks, then builds and smoke-tests the Docker image. No compiler job is included.

Pushes to `main`, `v*` tags and manual workflow runs publish the tested image to **`ghcr.io/mastermind-u/eonarq`** using the workflow's `GITHUB_TOKEN` with `packages: write`. Pull requests build/test without publishing. Main publishes `latest`; every publication includes a `sha-…` tag, and `v0.1.0` publishes `0.1.0`. The first image becomes available only after this workflow runs successfully in GitHub.

The workflow follows GitHub's [container publication guidance](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images). Docker packaging uses uv's [non-editable installation pattern](https://docs.astral.sh/uv/guides/integration/docker/).

## License

[GNU GPL v3.0](LICENSE).

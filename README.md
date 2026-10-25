# Eonarq

A local tracker for long-running epics, editable prompts and coding agents.

```text
Epic
  └─ Master task
       └─ Subtask
```

The web interface and MCP tools share one SQLite database and the same application use cases. No account or authentication is required. The default published address is loopback only.

- Create, edit, reorder, move and delete tasks through MCP or the HTTP API.
- Create, edit, complete and delete tasks in the web interface. Edit Markdown prompts at every level.
- The overview is an agile board with To do, In progress, Blocked and Done columns. Drag an epic by its handle to change its status, or use its status menu with a keyboard or touch screen.
- Open an epic to see its progress diagram, master tasks and subtasks. Progress is one compact field of squares; hover or focus a square to outline its master task. Click a square to edit its task and prompt.
- Metrics show leaf-task progress, closed epics/master tasks, work in progress and blocked work. The overview counts epics; an epic page counts its direct master tasks. WIP includes both in-progress and blocked cards.
- MCP can load the selected prompt together with its current epic/master context. Changes made in the browser are immediately available to agents; the browser refreshes external changes every five seconds while the editor is closed.

## Run with Docker (recommended)

Install Docker with Compose v2, then run from the repository root:

```sh
docker compose up -d --build
docker compose ps
```

Open **http://127.0.0.1:8765**.

| Endpoint | URL |
| --- | --- |
| Web interface | `http://127.0.0.1:8765/` |
| Streamable HTTP MCP | `http://127.0.0.1:8765/mcp` |
| Interactive HTTP API | `http://127.0.0.1:8765/docs` |
| Health | `http://127.0.0.1:8765/health` |

Migrations run before the server starts. Data lives in the `eonarq_data` named volume at `/data/eonarq.sqlite3`. Rebuilding the image, restarting, or running `docker compose down` preserves it; `down -v` deletes the volume.

```sh
docker compose logs -f eonarq
docker compose restart eonarq
docker compose down
```

To change the host port, put `EONARQ_PORT=8766` in a local `.env` file, then run Compose again and update the MCP client URL. The container continues to listen on port 8765.

### Run a published image

After CI has published the first image:

```sh
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

This uses `ghcr.io/mastermind-u/eonarq:latest` and the same named data volume. Set `EONARQ_TAG` in `.env` to a release tag such as `0.1.0` or a published `sha-…` tag. If the GHCR package is private, log in with `docker login ghcr.io` before pulling; make the package public in GitHub package settings for anonymous pulls.

### Back up the database

Use SQLite's backup API so the backup includes committed WAL changes:

```sh
docker compose exec -T eonarq python -c "import sqlite3; source = sqlite3.connect('/data/eonarq.sqlite3'); target = sqlite3.connect('/data/backup.sqlite3'); source.backup(target); target.close(); source.close()"
docker compose cp eonarq:/data/backup.sqlite3 ./backup.sqlite3
```

## Connect Codex

Start Eonarq with Docker or the native command below, then add its HTTP endpoint:

```sh
codex mcp add eonarq --url http://127.0.0.1:8765/mcp
codex mcp get eonarq
codex mcp list
```

Alternatively, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.eonarq]
url = "http://127.0.0.1:8765/mcp"
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
1. Read list_epics and get_board before changing the plan.
2. Read get_task and work_on_task for the selected task's latest prompt/context.
3. Keep the epic -> master -> subtask hierarchy.
4. Mark work in_progress before implementing, then done after its checks pass.
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
| `EONARQ_PORT` | `8765` | Listener port; Compose uses it for the host port |
| `EONARQ_ALLOWED_HOSTS` | `localhost;127.0.0.1;[::1]` | Semicolon-separated permitted Host values |
| `EONARQ_BROWSER_CHANNEL` | unset | Test-only Playwright channel, e.g. `msedge` |

Native environment example in PowerShell:

```powershell
$env:EONARQ_PORT = "8766"
$env:EONARQ_DATABASE_URL = "sqlite:///./data/another.sqlite3"
uv run eonarq
```

## Task and progress rules

- The hierarchy has exactly three levels. Epics have no parent; masters belong to epics; subtasks belong to masters. Moves preserve these rules and keep the task ID and descendants.
- States: `todo`, `in_progress`, `blocked`, `done`.
- A square represents a leaf: a subtask, or a master/epic that has no children. Each leaf has equal weight; progress measures completed leaves, not effort.
- Closing the last child does not automatically close its parent. A parent can be marked done only when every immediate child is done.
- Board moves use the same version checks and completion rules as HTTP/MCP commands. A rejected move keeps the card in its saved column and shows the reason.
- Adding an open child or reopening/moving an open descendant reopens completed ancestors as `in_progress`.
- Mutations require the current `expected_version`. A stale edit returns HTTP 409 or an MCP tool error, without overwriting newer data. On conflict, reload the task and reapply the intended change.
- Order is a nonnegative integer, then stable UUID order. Titles contain 1–200 characters; prompts contain up to 200,000 characters.
- Deletion with children requires `recursive=true`. The UI requests confirmation and applies recursive deletion explicitly.

## MCP surface

| Tool | Purpose |
| --- | --- |
| `list_epics` | Epic summaries and progress |
| `get_board(epic_id?)` | Task hierarchy, versions, progress squares and flow metrics |
| `get_task(task_id)` | Full task with editable prompt and current version |
| `get_task_prompt(task_id)` | Inherited epic/master/subtask context |
| `create_task(title, kind, parent_id?, prompt?, position?)` | Create work at the correct level |
| `update_task(task_id, expected_version, title?, prompt?, status?, position?)` | Edit selected fields; omitted fields stay unchanged |
| `move_task(task_id, parent_id, expected_version)` | Move a master or subtask |
| `delete_task(task_id, expected_version, recursive?)` | Explicit deletion |

MCP prompt: `work_on_task(task_id)`. Resources: `eonarq://epics`, `eonarq://tasks/{task_id}`. The prompt/resource reads current stored content on every call. Read tools advertise read-only annotations; deletion advertises destructive behavior.

Example: call `create_task` with `{"title":"Make ToDo app","kind":"epic","prompt":"Goal and acceptance criteria"}`. Use its returned `task_id` as the parent when creating a `master`, then the master's ID when creating a `subtask`.

## HTTP API

All payloads/responses and validation schemas are in `/docs`.

Board responses include `flow` counters (`total`, `todo`, `in_progress`, `blocked`, `done`, `wip`, `completion_percent`). An unscoped board summarizes epics; `epic_id` scopes the counters to that epic's master tasks. Each task also exposes `flow` for its immediate children. These counters describe explicit task statuses; leaf completion remains a separate progress measure.

| Method | Path | Input |
| --- | --- | --- |
| GET | `/api/planning/q/board` | Optional `epic_id` query parameter |
| GET | `/api/planning/q/tasks/{id}` | UUID path parameter |
| GET | `/api/planning/q/tasks/{id}/prompt` | UUID path parameter |
| POST | `/api/planning/c/create` | `title`, `kind`, optional `parent_id`, `prompt`, `position` |
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

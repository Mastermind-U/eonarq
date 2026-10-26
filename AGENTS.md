# Agents Guide

Eonarq is a local DDD/CQRS epic and prompt tracker. Synchronous FastAPI HTTP routes and MCP tools are adapters over the same synchronous application and SQLite persistence layers. Jinja serves the shell; browser JavaScript calls the HTTP API.

## Structure and dependencies

```text
src/eonarq/planning/{common,command,query}/{domain,application,infrastructure,presentation}/
src/eonarq/shared_kernel/{domain,application,infrastructure,presentation}/
src/eonarq/migrations/versions/
```

- Dependencies point inward: presentation and infrastructure depend on application/domain. Keep application and domain free of SQLAlchemy, FastAPI, Dishka, MCP, Jinja and transport schemas.
- Queries only read. Commands change state. Command/query entities and mappings are separate; slices do not import each other. Context common imports neither slice. Shared kernel imports no contexts. Outer adapters within a slice stay independent.
- Use flat operation modules, frozen/slotted DTOs in `application/dtos.py`, ports in `application/gateways.py`, validators in `application/common/validators.py`, pure rules in domain. Neutral persistence ports belong in shared application code.
- Entities inherit `BaseEntity`, use `dataclass(slots=True)` and create UUID7 in entity fields. Preserve IDs and tracked values on rollback. DTO names end in Input, Output or Data.
- Interactors use `dataclass(slots=True)` with typed dependencies; their only public method is `execute(Input)`. Local helpers start with `_`. Validate all adapters through application validators.
- Protocols describe roles; complete implementations and test doubles explicitly inherit them. Business errors inherit the context root and `BaseDomainException`; delivery translates them.
- Register adapters in context Dishka providers, normally REQUEST scoped. Root `ioc.py` composes providers and contains no gateway behavior or business rules.

## Persistence and transactions

- Use synchronous SQLAlchemy and standard SQLite. Build SQL from Tables/`.c`; Table references end in `_t`. Map command/query entities imperatively and load them natively, without row-to-entity reconstruction. Query mappings reject writes.
- Repositories only load. Shared `EntitySaver` stages additions/deletions; shared `TransactionManager` owns explicit begin/commit/rollback. No repository save/add or UnitOfWork.
- Use `autoflush=False`, `expire_on_commit=False`, WAL, foreign keys, SERIALIZABLE transactions and a bounded busy timeout. Commands acquire a SQLite writer reservation with BEGIN IMMEDIATE before mutable reads. Never use lock tables or no-op updates. Every failure rolls back, including commit failures.
- Serialize hierarchy checks with the write transaction. Use expected versions to reject stale edits. A completed parent cannot contain open children; reopening/adding an open descendant reopens completed ancestors. Parent completion is explicit.
- Migrate before serving; providers never create tables. Keep the pre-release schema in one initial Alembic revision. Package migrations/templates/static assets in the wheel and Docker image.

## Adapters and local scope

- HTTP uses `DishkaSyncRoute`, `FromDishka`, request scopes and `/api/planning/c` or `/api/planning/q`. Handlers convert input and call `execute`. Reuse DTOs as HTTP schemas when representations match.
- MCP transport is asynchronous ASGI, but each tool runs synchronous use cases in a worker thread with its own synchronous Dishka request scope. Never share sessions between calls or block the ASGI event loop with database work.
- Jinja serves templates; JavaScript uses the API. Render user titles/prompts with textContent/form values, never HTML. Keep prompts editable and shared between UI/API/MCP. No credentials, accounts or authentication.
- Default native binding and Docker publishing are loopback only. Keep same-origin write and host checks without adding an authentication flow. SQLite data must survive restart and image replacement.

## Running and checks

Python 3.14+, from the repository root:

```sh
uv sync --locked
uv run eonarq
```

Docker is the documented default: pull `ghcr.io/mastermind-u/eonarq:latest`, then use `docker run` with a persistent named volume and loopback port publishing as shown in README.md. Compose is an optional alternative using the published image. No source checkout, local build, native compilation or bundled executable is required. Backups use SQLite's online Backup API in the running container, then `docker cp` to copy the snapshot to the host without stopping the service.

For every changed Python file, run in order:

```sh
uv run ruff format <file>
uv run ruff check --fix --unsafe-fixes <file>
```

Final checks:

```sh
uv run lint-imports
uv run pytest tests/units
uv run pytest tests/integrations
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
git diff --check
```

- Do not weaken checks. Units cover pure rules and interactor success/failure/rollback branches; integrations use temporary SQLite files, real transactions and the HTTP/MCP adapters. Run tests on the host, not inside Docker. Keep unit and integration CI jobs separate; build/publish the image only after checks pass.
- Use up to four pytest workers; `-n 0` for debugging/coverage. Override Dishka with test providers/context. Concurrency and persistence tests use independent sessions and real commits.
- Check browser interactions, hover contours and narrow screens for UI changes. Tie MCP and Docker claims to real protocol/container runs; distinguish configured publishing from an actual registry push.

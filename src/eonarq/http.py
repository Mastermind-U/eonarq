from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from anyio import to_thread
from dishka import Container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse

from eonarq.ioc import create_container
from eonarq.mcp import create_mcp_server
from eonarq.planning.command.presentation.http import router as commands
from eonarq.planning.common.presentation.http import (
    register_exception_handlers,
)
from eonarq.planning.query.presentation.http import router as queries
from eonarq.shared_kernel.infrastructure.config import Config, load_config
from eonarq.shared_kernel.infrastructure.migrations import migrate
from eonarq.shared_kernel.presentation.origin import SameOriginMiddleware


def create_app(
    config: Config | None = None,
    container: Container | None = None,
) -> FastAPI:
    config = config or load_config()
    owns_container = container is None
    container = container or create_container(config)
    server = create_mcp_server(container, config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            await to_thread.run_sync(migrate, config)
            async with server.session_manager.run():
                yield
        finally:
            if owns_container:
                await to_thread.run_sync(container.close)

    app = FastAPI(title="Eonarq", version="0.1.0", lifespan=lifespan)
    setup_dishka(container, app)
    app.add_middleware(SameOriginMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(config.allowed_hosts),
    )
    register_exception_handlers(app)
    app.include_router(commands)
    app.include_router(queries)
    assets = Path(__file__).parent
    templates = Jinja2Templates(directory=assets / "templates")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"version": "0.1.0"},
        )

    @app.get("/health", tags=["Runtime"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    app.mount(
        "/static",
        StaticFiles(directory=assets / "static"),
        name="static",
    )
    app.mount("/", server.streamable_http_app())
    return app

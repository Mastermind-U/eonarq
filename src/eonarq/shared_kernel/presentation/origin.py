from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class SameOriginMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Reject cross-origin writes; allow local MCP clients."""
        if scope["type"] == "http" and scope["method"] not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            headers = dict(scope["headers"])
            origin = headers.get(b"origin")
            expected = (
                scope["scheme"].encode() + b"://" + headers.get(b"host", b"")
            )
            if origin is not None and origin != expected:
                response = JSONResponse(
                    {"detail": "Cross-origin writes are not allowed"},
                    status_code=403,
                )
                await response(scope, receive, send)
                return
        await self._app(scope, receive, send)

from dishka import Container
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from eonarq.planning.command.presentation.mcp import register_command_tools
from eonarq.planning.query.presentation.mcp import register_query_tools
from eonarq.shared_kernel.infrastructure.config import Config


def create_mcp_server(container: Container, config: Config) -> FastMCP:
    server = FastMCP(
        "Eonarq",
        instructions=(
            "Local epic → master → subtask tracker. Read get_board, then "
            "get_task for the latest editable prompt and version. "
            "Mutate through tools; expected_version prevents stale edits. "
            "Parent completion is explicit. Use work_on_task for context."
        ),
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                pattern
                for host in config.allowed_hosts
                for pattern in (host, host + ":*")
            ],
            allowed_origins=[
                scheme + "://" + host + ":*"
                for host in config.allowed_hosts
                for scheme in ("http", "https")
            ],
        ),
    )
    register_command_tools(server, container)
    register_query_tools(server, container)
    return server

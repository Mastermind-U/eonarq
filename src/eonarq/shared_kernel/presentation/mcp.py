from collections.abc import Callable
from functools import partial

from anyio import to_thread
from dishka import Container
from mcp.server.fastmcp.exceptions import ToolError

from eonarq.shared_kernel.domain.exceptions import BaseDomainException


def _execute[T](
    container: Container,
    operation: Callable[[Container], T],
) -> T:
    try:
        with container() as request:
            return operation(request)
    except BaseDomainException as error:
        raise ToolError(str(error)) from error


async def run_in_request[T](
    container: Container,
    operation: Callable[[Container], T],
) -> T:
    return await to_thread.run_sync(partial(_execute, container, operation))

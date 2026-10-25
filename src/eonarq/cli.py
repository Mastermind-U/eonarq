import argparse
from dataclasses import replace

import uvicorn

from eonarq.http import create_app
from eonarq.shared_kernel.infrastructure.config import load_config
from eonarq.shared_kernel.infrastructure.migrations import migrate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Eonarq local epic and prompt tracker",
    )
    parser.add_argument("--host", help="Listener host (default: 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        help="Listener port (default: 8765)",
    )
    parser.add_argument("--database", help="Synchronous SQLite URL")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Apply migrations and exit",
    )
    args = parser.parse_args()
    config = load_config()
    config = replace(
        config,
        HOST=args.host or config.HOST,
        PORT=args.port if args.port is not None else config.PORT,
        DATABASE_URL=args.database or config.DATABASE_URL,
    )
    if args.init_db:
        migrate(config)
        return
    uvicorn.run(create_app(config), host=config.HOST, port=config.PORT)

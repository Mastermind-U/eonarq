from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig

from eonarq.shared_kernel.infrastructure.config import Config
from eonarq.shared_kernel.infrastructure.database import create_database_engine


def migrate(config: Config) -> None:
    alembic = AlembicConfig()
    alembic.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[2] / "migrations"),
    )
    engine = create_database_engine(config)
    try:
        with engine.begin() as connection:
            alembic.attributes["connection"] = connection
            command.upgrade(alembic, "head")
    finally:
        engine.dispose()

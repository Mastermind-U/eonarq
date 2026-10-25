from collections.abc import Iterator
from pathlib import Path

import pytest
from dishka import Container
from fastapi.testclient import TestClient

from eonarq.http import create_app
from eonarq.ioc import create_container
from eonarq.shared_kernel.infrastructure.config import Config
from eonarq.shared_kernel.infrastructure.migrations import migrate


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        DATABASE_URL="sqlite:///" + str(tmp_path / "tracker.sqlite3"),
    )


@pytest.fixture
def container(config: Config) -> Iterator[Container]:
    migrate(config)
    container = create_container(config)
    try:
        yield container
    finally:
        container.close()


@pytest.fixture
def client(config: Config) -> Iterator[TestClient]:
    with TestClient(create_app(config), base_url="http://127.0.0.1") as client:
        yield client

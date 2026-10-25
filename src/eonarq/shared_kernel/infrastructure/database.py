from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Connection,
    Engine,
    MetaData,
    create_engine,
    event,
    inspect,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, attributes, registry

from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)
from eonarq.shared_kernel.domain.entities import BaseEntity
from eonarq.shared_kernel.infrastructure.config import Config

metadata = MetaData()
mapper_registry = registry(metadata=metadata)


def create_database_engine(config: Config) -> Engine:
    url = make_url(config.DATABASE_URL)
    if url.database and url.database != ":memory:":
        Path(url.database).resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 10},
        isolation_level="SERIALIZABLE",
    )

    @event.listens_for(engine, "connect")
    def configure(connection: Any, _record: Any) -> None:
        connection.isolation_level = None
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA read_uncommitted=0")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    @event.listens_for(engine, "begin")
    def begin(connection: Connection) -> None:
        mode = (
            "BEGIN IMMEDIATE"
            if connection.get_execution_options().get("eonarq_write")
            else "BEGIN"
        )
        connection.exec_driver_sql(mode)

    return engine


def open_session(engine: Engine) -> Iterator[Session]:
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        session.info["snapshots"] = {}

        @event.listens_for(session, "loaded_as_persistent")
        def capture(loaded_session: Session, entity: BaseEntity) -> None:
            state = inspect(entity)
            if state is None:
                raise TypeError("Cannot snapshot an unmapped entity")
            snapshot = {
                attribute.key: deepcopy(getattr(entity, attribute.key))
                for attribute in state.mapper.column_attrs
            }
            loaded_session.info["snapshots"][id(entity)] = (entity, snapshot)

        yield session


class SQLAlchemyEntitySaver(EntitySaver):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: BaseEntity) -> None:
        self._session.add(entity)

    def delete(self, entity: BaseEntity) -> None:
        self._session.delete(entity)


class SQLiteTransactionManager(TransactionManager):
    def __init__(self, session: Session) -> None:
        self._session = session

    def begin(self) -> None:
        if self._session.in_transaction():
            raise RuntimeError("Commands require a fresh request transaction")
        self._session.connection(execution_options={"eonarq_write": True})

    def commit(self) -> None:
        self._session.commit()
        self._session.info["snapshots"].clear()

    def rollback(self) -> None:
        snapshots = list(self._session.info["snapshots"].values())
        self._session.rollback()
        for entity, values in snapshots:
            for name, value in values.items():
                attributes.set_committed_value(entity, name, value)
        self._session.info["snapshots"].clear()

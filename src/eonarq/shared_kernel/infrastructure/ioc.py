from collections.abc import Iterable

from dishka import Provider, Scope, from_context, provide
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)
from eonarq.shared_kernel.infrastructure.config import Config
from eonarq.shared_kernel.infrastructure.database import (
    SQLAlchemyEntitySaver,
    SQLiteTransactionManager,
    create_database_engine,
    open_session,
)


class PersistenceProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def engine(self, config: Config) -> Iterable[Engine]:
        engine = create_database_engine(config)
        try:
            yield engine
        finally:
            engine.dispose()

    @provide(scope=Scope.REQUEST)
    def session(self, engine: Engine) -> Iterable[Session]:
        yield from open_session(engine)

    saver = provide(
        SQLAlchemyEntitySaver,
        provides=EntitySaver,
        scope=Scope.REQUEST,
    )
    transaction = provide(
        SQLiteTransactionManager,
        provides=TransactionManager,
        scope=Scope.REQUEST,
    )

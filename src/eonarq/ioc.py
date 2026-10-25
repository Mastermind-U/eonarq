from dishka import Container, make_container

from eonarq.planning.command.infrastructure.ioc import PlanningCommandProvider
from eonarq.planning.query.infrastructure.ioc import PlanningQueryProvider
from eonarq.shared_kernel.infrastructure.config import Config
from eonarq.shared_kernel.infrastructure.ioc import PersistenceProvider


def create_container(config: Config) -> Container:
    return make_container(
        PersistenceProvider(),
        PlanningCommandProvider(),
        PlanningQueryProvider(),
        context={Config: config},
    )

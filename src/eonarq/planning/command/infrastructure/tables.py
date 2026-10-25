from eonarq.planning.command.domain.entities import Task as Task
from eonarq.planning.common.infrastructure.tables import tasks_t
from eonarq.shared_kernel.infrastructure.database import mapper_registry

mapper_registry.map_imperatively(Task, tasks_t)

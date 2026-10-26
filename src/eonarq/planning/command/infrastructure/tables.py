from eonarq.planning.command.domain.entities import (
    Project as Project,
    Task as Task,
)
from eonarq.planning.common.infrastructure.tables import projects_t, tasks_t
from eonarq.shared_kernel.infrastructure.database import mapper_registry

mapper_registry.map_imperatively(Task, tasks_t)
mapper_registry.map_imperatively(Project, projects_t)

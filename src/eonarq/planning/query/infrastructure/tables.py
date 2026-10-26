from typing import Any

from sqlalchemy import event

from eonarq.planning.common.domain.exceptions import InvalidTask
from eonarq.planning.common.infrastructure.tables import projects_t, tasks_t
from eonarq.planning.query.domain.entities import (
    ProjectRecord as ProjectRecord,
    TaskRecord as TaskRecord,
)
from eonarq.shared_kernel.infrastructure.database import mapper_registry

mapper_registry.map_imperatively(TaskRecord, tasks_t)
mapper_registry.map_imperatively(ProjectRecord, projects_t)


@event.listens_for(TaskRecord, "before_insert")
@event.listens_for(TaskRecord, "before_update")
@event.listens_for(TaskRecord, "before_delete")
@event.listens_for(ProjectRecord, "before_insert")
@event.listens_for(ProjectRecord, "before_update")
@event.listens_for(ProjectRecord, "before_delete")
def reject_query_write(
    _mapper: Any,
    _connection: Any,
    _target: TaskRecord | ProjectRecord,
) -> None:
    raise InvalidTask("Query entities are read-only")

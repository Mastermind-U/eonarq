from dataclasses import dataclass

from eonarq.planning.command.application.common.validators import (
    validate_create_project,
)
from eonarq.planning.command.application.dtos import (
    CreateProjectInput,
    ProjectMutationOutput,
)
from eonarq.planning.command.domain.entities import Project
from eonarq.shared_kernel.application.gateways import (
    EntitySaver,
    TransactionManager,
)


@dataclass(slots=True)
class CreateProject:
    saver: EntitySaver
    transaction: TransactionManager

    def execute(self, data: CreateProjectInput) -> ProjectMutationOutput:
        validate_create_project(data)
        try:
            self.transaction.begin()
            project = Project(data.title, data.prompt)
            self.saver.add(project)
            self.transaction.commit()
            return ProjectMutationOutput(project.id, project.version)
        except BaseException:
            self.transaction.rollback()
            raise

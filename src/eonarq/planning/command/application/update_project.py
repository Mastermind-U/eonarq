from dataclasses import dataclass

from eonarq.planning.command.application.common.validators import (
    validate_update_project,
)
from eonarq.planning.command.application.dtos import (
    ProjectMutationOutput,
    UpdateProjectInput,
)
from eonarq.planning.command.application.gateways import TaskRepository
from eonarq.shared_kernel.application.gateways import TransactionManager


@dataclass(slots=True)
class UpdateProject:
    repository: TaskRepository
    transaction: TransactionManager

    def execute(self, data: UpdateProjectInput) -> ProjectMutationOutput:
        validate_update_project(data)
        try:
            self.transaction.begin()
            project = self.repository.load_project(data.project_id)
            project.ensure_version(data.expected_version)
            if data.title is not None:
                project.title = data.title.strip()
            if data.prompt is not None:
                project.prompt = data.prompt
            project.version += 1
            self.transaction.commit()
            return ProjectMutationOutput(project.id, project.version)
        except BaseException:
            self.transaction.rollback()
            raise

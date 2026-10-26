from dataclasses import dataclass

from eonarq.planning.query.application.dtos import ProjectData, ProjectsInput
from eonarq.planning.query.application.gateways import TaskReader


@dataclass(slots=True)
class ListProjects:
    reader: TaskReader

    def execute(self, _data: ProjectsInput) -> tuple[ProjectData, ...]:
        return tuple(
            ProjectData(
                project.id,
                project.title,
                project.prompt,
                project.version,
            )
            for project in self.reader.list_projects()
        )

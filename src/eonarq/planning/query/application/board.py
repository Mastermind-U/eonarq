from dataclasses import dataclass
from uuid import UUID

from eonarq.planning.common.domain.exceptions import InvalidTask, TaskNotFound
from eonarq.planning.common.domain.types import TaskKind, TaskStatus
from eonarq.planning.query.application.common.metrics import summarize_flow
from eonarq.planning.query.application.common.validators import validate_id
from eonarq.planning.query.application.dtos import (
    BoardInput,
    BoardOutput,
    CellData,
    TaskData,
)
from eonarq.planning.query.application.gateways import TaskReader
from eonarq.planning.query.domain.entities import TaskRecord


@dataclass(slots=True)
class GetBoard:
    reader: TaskReader

    def execute(self, data: BoardInput) -> BoardOutput:
        validate_id(data.epic_id, optional=True)
        validate_id(data.project_id, optional=True)
        if data.project_id is not None:
            self.reader.load_project(data.project_id)
        records = self.reader.load_all(data.project_id)
        by_id = {task.id: task for task in records}
        if data.epic_id is not None:
            if data.epic_id not in by_id:
                raise TaskNotFound("Epic not found")
            if by_id[data.epic_id].kind != TaskKind.EPIC:
                raise InvalidTask("Board scope must be an epic")
        children: dict[UUID | None, list[TaskRecord]] = {}
        for task in records:
            children.setdefault(task.parent_id, []).append(task)
        for group in children.values():
            group.sort(key=lambda task: (task.position, task.id))
        summaries: list[TaskData] = []
        cells: list[CellData] = []
        roots = (
            [by_id[data.epic_id]] if data.epic_id else children.get(None, [])
        )
        for epic in roots:
            self._visit(epic, epic.id, None, children, summaries, cells)
        done = sum(cell.status == TaskStatus.DONE for cell in cells)
        total = sum(cell.status != TaskStatus.CANCELLED for cell in cells)
        return BoardOutput(
            tuple(summaries),
            tuple(cells),
            done,
            total,
            round(done / total * 100, 1) if total else 0,
            summarize_flow(
                children.get(data.epic_id, [])
                if data.epic_id
                else records
                if data.project_id
                else roots,
            ),
        )

    def _visit(
        self,
        task: TaskRecord,
        epic_id: UUID,
        master_id: UUID | None,
        children: dict[UUID | None, list[TaskRecord]],
        summaries: list[TaskData],
        cells: list[CellData],
    ) -> tuple[int, int]:
        if task.kind == TaskKind.MASTER:
            master_id = task.id
        descendants = children.get(task.id, [])
        if descendants:
            progress = [
                self._visit(
                    child,
                    epic_id,
                    master_id,
                    children,
                    summaries,
                    cells,
                )
                for child in descendants
            ]
            done, total = (
                sum(item[0] for item in progress),
                sum(item[1] for item in progress),
            )
        else:
            done, total = (
                int(task.status == TaskStatus.DONE),
                int(task.status != TaskStatus.CANCELLED),
            )
            cells.append(
                CellData(task.id, epic_id, master_id, task.title, task.status),
            )
        summaries.append(
            TaskData(
                task.id,
                task.parent_id,
                task.kind,
                task.title,
                task.status,
                task.position,
                task.version,
                done,
                total,
                round(done / total * 100, 1) if total else 0,
                summarize_flow(descendants),
                task.project_id,
                task.action,
            ),
        )
        return done, total

from collections import Counter
from collections.abc import Sequence

from eonarq.planning.common.domain.types import TaskStatus
from eonarq.planning.query.application.dtos import FlowMetricsData
from eonarq.planning.query.domain.entities import TaskRecord


def summarize_flow(tasks: Sequence[TaskRecord]) -> FlowMetricsData:
    counts = Counter(task.status for task in tasks)
    done = counts[TaskStatus.DONE]
    in_progress = counts[TaskStatus.IN_PROGRESS]
    blocked = counts[TaskStatus.BLOCKED]
    return FlowMetricsData(
        total=len(tasks),
        todo=counts[TaskStatus.TODO],
        in_progress=in_progress,
        blocked=blocked,
        done=done,
        wip=in_progress + blocked,
        completion_percent=round(done / len(tasks) * 100, 1) if tasks else 0,
    )

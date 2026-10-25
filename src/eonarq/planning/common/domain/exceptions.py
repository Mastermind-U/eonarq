from eonarq.shared_kernel.domain.exceptions import BaseDomainException


class PlanningException(BaseDomainException):
    pass


class InvalidTask(PlanningException):
    pass


class TaskNotFound(PlanningException):
    pass


class TaskConflict(PlanningException):
    pass

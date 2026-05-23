from enum import Enum


class ExperimentSortKey(str, Enum):
    NAME = "name"
    CREATED_AT = "created_at"


class OutputLevel(Enum):
    """Represents the severity level for operation results."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

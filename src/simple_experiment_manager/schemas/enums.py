from enum import Enum


class ExperimentSortKey(str, Enum):
    NAME = "name"
    CREATED_AT = "created_at"

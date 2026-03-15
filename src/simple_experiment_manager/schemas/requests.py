from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from simple_experiment_manager.schemas.contexts import ConfigClass
from simple_experiment_manager.schemas.validators import validate_safe_name


# experiments
class RequestCreateExperiment(BaseModel):
    # model configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # fields
    experiment_name: Annotated[
        str | None,
        Field(
            description="The identifier for the new experiment to create. If None, the directory name is assigned."
        ),
    ] = Field(default=None)
    dir_name: Annotated[
        str | None,
        Field(
            description="The actual experiment directory name to create. If None, automatically assigned, such as 'exp_001'."
        ),
    ] = Field(default=None)
    config: Annotated[
        BaseModel | ConfigClass | None,
        Field(
            description="The actual configuration instance. If None, the default config is used."
        ),
    ] = Field(default=None)
    description: Annotated[
        str, Field(description="A brief summary of the experiment to create.")
    ] = Field(default="")

    @field_validator("dir_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        return validate_safe_name(v) if isinstance(v, str) else None


class RequestSetActiveExperiment(BaseModel):
    experiment_name: Annotated[
        str | None,
        Field(
            description="The name of the experiment to set as active. If None, unsets the active experiment."
        ),
    ]


class RequestDeleteExperiment(BaseModel):
    experiment_name: Annotated[
        str, Field(description="The name of the experiment to delete.")
    ]


class RequestCopyExperiment(BaseModel):
    src_experiment_name: Annotated[
        str, Field(description="The name of the source experiment to copy from.")
    ]
    dst_experiment_name: Annotated[
        str, Field(description="The name of the destination experiment to copy to.")
    ]
    dst_dir_name: Annotated[
        str | None,
        Field(
            description="The actual experiment directory name to create by copy. If None, automatically assigned, such as 'exp_001'"
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            description="A new description for the copied experiment. If None, copies from the source experiment."
        ),
    ] = Field(default=None)

    @field_validator("dst_dir_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        return validate_safe_name(v) if isinstance(v, str) else None


class RequestUpdateExperimentConfig(BaseModel):
    # model configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # fields
    experiment_name: Annotated[
        str, Field(description="The name of the experiment to update configuration.")
    ]
    config: Annotated[
        BaseModel | ConfigClass, Field(description="The new configuration instance.")
    ]


class RequestUpdateExperimentDescription(BaseModel):
    experiment_name: Annotated[
        str, Field(description="The name of the experiment to update description.")
    ]
    description: Annotated[
        str, Field(description="The new description for the specified experiment.")
    ]


class RequestRenameExperiment(BaseModel):
    old_experiment_name: Annotated[
        str, Field(description="The current name of the experiment to rename.")
    ]
    new_experiment_name: Annotated[
        str, Field(description="The new name of the experiment to rename.")
    ]


class RequestGetExperimentConfig(BaseModel):
    experiment_name: Annotated[
        str,
        Field(
            description="The name of the experiment whose configuration is to be retrieved."
        ),
    ]


# labels
class RequestAddLabelsToExperiment(BaseModel):
    experiment_name: Annotated[
        str,
        Field(description="The name of the experiment to add labels to."),
    ]
    labels: Annotated[list[str], Field(description="A list of label names to add.")]


class RequestRemoveGlobalLabels(BaseModel):
    labels: Annotated[
        list[str],
        Field(
            description="A list of label names to remove globally and from all experiments."
        ),
    ]


class RequestUpdateExperimentLabels(BaseModel):
    experiment_name: Annotated[
        str, Field(description="The name of the experiment to update.")
    ]
    labels: Annotated[
        list[str], Field(description="A list of labels to assign to the experiment.")
    ]


class RequestGetLabelUsage(BaseModel):
    pass


class RequestGetExperimentLabelMap(BaseModel):
    experiment_name: Annotated[
        str, Field(description="The name of the experiment to check label usage.")
    ]


# index
class RequestGetIndex(BaseModel):
    pass

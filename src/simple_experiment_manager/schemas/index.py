from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from simple_experiment_manager.schemas.validators import ensure_unique_list


class ExperimentMetadata(BaseModel):
    """Metadata for an individual experiment."""

    # model configuration
    model_config = ConfigDict(validate_assignment=True)

    # fields
    created_at: Annotated[
        datetime,
        Field(
            description="The datetime when the experiment is created.",
        ),
    ] = Field(default_factory=datetime.now)
    labels: Annotated[
        list[str], Field(description="Labels that the experiment has.")
    ] = Field(default_factory=list)
    relative_config_path: Annotated[
        Path,
        Field(description="Path to the config file　relative to the experiment root."),
    ]
    description: Annotated[
        str, Field(description="Brief summary of the experiment.")
    ] = Field(default="")

    @field_validator("labels", mode="after")
    @classmethod
    def validate_labels(cls, v: list[str]) -> list[str]:
        return ensure_unique_list(v)

    @property
    def dir_name(self) -> str:
        """Returns the physical directory name extracted from config_path."""
        return self.relative_config_path.parent.name

    def get_full_config_path(self, root: Path) -> Path:
        """Gets the full configuration file path based on the experiment root."""
        return root / self.relative_config_path

    def get_full_dir_path(self, root: Path) -> Path:
        """Gets the full experiment directory path based on the experiment root."""
        return root / self.relative_config_path.parent


class ExperimentIndex(BaseModel):
    """The master index for all experiments managed by the library."""

    # model configuration
    model_config = ConfigDict(validate_assignment=True)

    # fields
    active_experiment: Annotated[
        str | None, Field(description="The active experiment name.")
    ] = None
    global_labels: Annotated[
        list[str],
        Field(description="Available experiment labels　to group experiments."),
    ] = Field(default_factory=list)
    experiments: Annotated[
        dict[str, ExperimentMetadata],
        Field(description="A dictionary of experiment metadata"),
    ] = Field(default_factory=dict)

    @field_validator("global_labels", mode="after")
    @classmethod
    def validate_labels(cls, v: list[str]) -> list[str]:
        return ensure_unique_list(v)

    def get_experiment_metadata(self, experiment_name: str) -> ExperimentMetadata:
        """Gets the metadata of the experiment."""
        experiment_name = self._validate_experiment_existence(experiment_name)
        return self.experiments[experiment_name]

    def get_experiment_config(self, root: Path, experiment_name: str) -> Path:
        """Gets the path to the experiment config file."""
        experiment_name = self._validate_experiment_existence(experiment_name)
        return self.experiments[experiment_name].get_full_config_path(root)

    def get_experiment_dir(self, root: Path, experiment_name: str) -> Path:
        """Gets the path to the experiment directory."""
        experiment_name = self._validate_experiment_existence(experiment_name)
        return self.experiments[experiment_name].get_full_dir_path(root)

    def get_experiment_labels(self, experiment_name: str) -> list[str]:
        """Gets the list of labels for the specified experiment."""
        experiment_name = self._validate_experiment_existence(experiment_name)
        return self.experiments[experiment_name].labels

    def get_experiment_description(self, experiment_name: str) -> str:
        """Gets the description for the specified experiment."""
        experiment_name = self._validate_experiment_existence(experiment_name)
        return self.experiments[experiment_name].description

    def purge_global_labels(self, labels_to_remove: list[str]) -> None:
        """Purges labels from the global list and removes them from all experiments."""
        target_set = set(labels_to_remove)

        # remove labels from the global labels
        self.global_labels = [
            label for label in self.global_labels if label not in target_set
        ]

        # clean up labels in every experiment
        for meta in self.experiments.values():
            meta.labels = [label for label in meta.labels if label not in target_set]

    def _validate_experiment_existence(self, experiment_name: str) -> str:
        if experiment_name not in self.experiments:
            raise ValueError(f"The experiment '{experiment_name}' does not exist.")
        return experiment_name

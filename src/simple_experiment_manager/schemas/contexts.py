from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

from simple_experiment_manager.schemas.validators import validate_safe_name


class ConfigClass:
    def __init__(self, **kwargs: Any):
        fields: dict[str, Any] = {k: (type(v), v) for k, v in kwargs.items()}
        self._Model = create_model(
            "ConfigClass",
            __config__=ConfigDict(arbitrary_types_allowed=True),
            **fields,
        )
        self._instance = self._Model.model_validate(kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._instance, name)

    def __repr__(self) -> str:
        data = self._instance.model_dump(fallback=lambda v: str(v))
        return f"{self._Model.__name__}({data})"

    def to_dict(self, mode: Literal["python", "json"] = "python") -> dict[str, Any]:
        """Converts the config instance into a dictionary.

        Args:
            mode:　The mode in which `model_dump` should run.\n
            - "python": Returns a dict with Python objects (default)
            - "json": Returns a JSON-serializable dict, unserializable objects are converted into string ones.
        """
        if mode == "json":
            return self._instance.model_dump(mode="json", fallback=lambda v: str(v))
        return self._instance.model_dump()

    @property
    def model_type(self) -> type[BaseModel]:
        return self._Model


class ExperimentContext(BaseModel):
    # configuration of the `ExperimentContext` class
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # fields
    default_config: Annotated[
        BaseModel | ConfigClass,
        Field(
            description="The default experiment configuration instance for a new experiment."
        ),
    ]
    base_dir: Annotated[
        Path,
        Field(description="Path to the parent directory of the experiment root."),
    ] = Path.home() / "Documents" / "simple_experiment_manager"
    experiment_root_name: Annotated[
        str,
        Field(description="The directory name where all experiments will be stored."),
    ] = Field(default="experiments")
    config_file_name: Annotated[
        str,
        Field(
            description="Filename for the experiment configuration. Supported formats: JSON, YAML."
        ),
    ] = "config.yaml"
    index_file_name: Annotated[
        str,
        Field(
            description="Filename for the global experiment index. Supported formats: JSON, YAML."
        ),
    ] = "experiment_index.json"
    experiment_dir_prefix: Annotated[
        str, Field(description="Prefix for auto-generated experiment dirctory names.")
    ] = Field(default="exp_")
    experiment_dir_digits: Annotated[
        int,
        Field(
            ge=1,
            le=10,
            description="Number of digits for auto-generated experiment directory serial numbers.",
        ),
    ] = Field(default=3)
    encoding: Annotated[
        str, Field(description="File encoding for the config file.")
    ] = "utf-8"
    indent: Annotated[
        int, Field(ge=0, le=8, description="Indentation level for JSON/YAML.")
    ] = 2
    dir_permission: Annotated[
        int | None,
        Field(description="Directory permission. `None` provides the OS default."),
    ] = 0o755
    file_permission: Annotated[
        int | None,
        Field(description="File permission. `None` provides the OS default."),
    ] = 0o644

    @field_validator("config_file_name", "index_file_name")
    @classmethod
    def validate_file_extension(cls, v: str) -> str:
        if not v.lower().endswith((".json", ".yaml", ".yml")):
            raise ValueError(
                f"Configuration files must be in JSON or YAML format. Received: {v}"
            )
        else:
            return v

    @field_validator("experiment_root_name", "config_file_name", "index_file_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_safe_name(v)

    @property
    def experiment_root(self) -> Path:
        """Path to the root directory for all experiments."""
        return self.base_dir / self.experiment_root_name

    @property
    def experiment_index_file(self) -> Path:
        """Path to the experiment index file."""
        return self.experiment_root / self.index_file_name

    @property
    def project_name(self) -> str:
        """The name of the project, derived from the base directory name."""
        return self.base_dir.name

    def get_experiment_dir(self, dir_name: str) -> Path:
        """Gets the directory path for a specific experiment directory."""
        return self.experiment_root / dir_name

    def get_config_file_from_dir(self, dir_name: str) -> Path:
        """Gets the configuration file path for a specific experiment directory."""
        return self.get_experiment_dir(dir_name) / self.config_file_name

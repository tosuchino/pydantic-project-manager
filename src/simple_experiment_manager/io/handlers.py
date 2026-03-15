import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from simple_experiment_manager.io.json_handler import (
    load_data_from_json,
    save_data_to_json,
)
from simple_experiment_manager.io.yaml_handler import (
    load_data_from_yaml,
    save_data_to_yaml_with_comments,
)
from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext
from simple_experiment_manager.schemas.index import ExperimentIndex


class ExperimentDataIO:
    """IO handler for experiment-specific files using ExperimentContext."""

    def __init__(self, ctx: ExperimentContext):
        self.ctx = ctx

    def save_config(
        self,
        path: Path,
        config: BaseModel | ConfigClass,
        comments: dict[str, str] | None = None,
    ) -> None:
        """Saves an experiment-specific configuration to the relevant file.

        This method handles several key transformations:
        1. Serialization: Converts Pydantic models or ConfigClass instances into JSON-compatible dictionaries.
        2. Fallback Handling: Any objects that are not natively JSON-serializable
        (e.g., functions, custom classes) are automatically converted to strings.
        3. Comment Extraction: If `config` is a Pydantic model and `comments` is None,
        it automatically extracts field descriptions to use as YAML comments.

        Args:
            path: Path to the configuration file to save.
            config: The configuration instance to save.
            comments: Optional dictionary mapping field names to comments. Overrides auto-extracted descriptions.
        """
        # ensure the given path is within the experiment root
        path = self._ensure_within_root(path)

        target_inst = config if isinstance(config, BaseModel) else config._instance
        data = target_inst.model_dump(mode="json", fallback=lambda v: str(v))

        if isinstance(config, BaseModel) and comments is None:
            comments = {
                k: v.description
                for k, v in config.__class__.model_fields.items()
                if v.description
            }
        StructuredDataIO.save(
            path=path,
            data=data,
            comments=comments,
            indent=self.ctx.indent,
            file_permission=self.ctx.file_permission or 0o644,
            dir_permission=self.ctx.dir_permission or 0o755,
            encoding=self.ctx.encoding,
        )

    def load_config(self, path: Path) -> BaseModel | ConfigClass:
        """Loads a experiment-specific configuration from the relevant file."""
        data = StructuredDataIO.load(path=path, encoding=self.ctx.encoding)

        if isinstance(self.ctx.default_config, BaseModel):
            return self.ctx.default_config.__class__.model_validate(data)
        else:
            return ConfigClass(**data)

    def save_index(self, experiment_index: ExperimentIndex) -> None:
        """Saves the `ExperimentIndex` instance to the index file."""
        # ensure the index file path is within the experiment root
        path = self.ctx.experiment_index_file
        path = self._ensure_within_root(path)
        StructuredDataIO.save(
            path=path,
            data=experiment_index.model_dump(mode="json"),
            indent=self.ctx.indent,
            file_permission=self.ctx.file_permission or 0o644,
            dir_permission=self.ctx.dir_permission or 0o755,
            encoding=self.ctx.encoding,
        )

    def load_index(self) -> ExperimentIndex:
        """Loads the `ExperimentIndex` instance from the experiment index file."""
        # ensure the index file is within the experiment root
        path = self.ctx.experiment_index_file
        path = self._ensure_within_root(path)
        
        if not path.exists():
            return ExperimentIndex()
        data = StructuredDataIO.load(
            path=self.ctx.experiment_index_file, encoding=self.ctx.encoding
        )
        return ExperimentIndex.model_validate(data)

    def delete_experiment_data(self, path: Path) -> None:
        """Deletes the experiment directory and all its contents.

        Args:
            path: Path to the experiment directory to delete.
        """
        # ensure the given path is within the experiment root
        target_path = self._ensure_within_root(path)

        if target_path.exists() and target_path.is_dir():
            shutil.rmtree(target_path)

    def rename_experiment_dir(self, old_path: Path, new_path: Path) -> None:
        """Renames the experiment directory."""
        # ensure the given paths are within the experiment root
        old_path = self._ensure_within_root(old_path)
        new_path = self._ensure_within_root(new_path)

        if not old_path.exists():
            raise FileNotFoundError(f"Source directory '{old_path}' not found.")
        if new_path.exists():
            raise FileExistsError(f"Destination '{new_path}' already exists.")
        old_path.rename(new_path)

    def _ensure_within_root(self, path: Path) -> Path:
        """Ensures the given path is under the experiment root."""
        target = path.resolve()
        experiment_root = self.ctx.experiment_root

        if target == experiment_root:
            raise ValueError(f"Cannot operate on the experiment root itself: {target}")

        if experiment_root not in target.parents:
            raise ValueError(
                f"Safety Violation: {path} is outside of the experiment root: {experiment_root}."
            )

        return target


class StructuredDataIO:
    """A specialized IO handler for structured text data (JSON and YAML).

    Note: This handler does not support binary files (e.g., images) or tabular data (e.g., CSV).
    """

    @staticmethod
    def is_json(path: Path) -> bool:
        """Checks if the file extension is JSON."""
        return path.suffix.lower() == ".json"

    @staticmethod
    def is_yaml(path: Path) -> bool:
        """Checks if the file extension is YAML."""
        return path.suffix.lower() in (".yaml", ".yml")

    @classmethod
    def save(
        cls,
        path: Path,
        data: dict[str, Any],
        *,
        comments: dict[str, str] | None = None,
        indent: int = 2,
        file_permission: int = 0o644,
        dir_permission: int = 0o755,
        encoding: str = "utf-8",
    ) -> None:
        """Saves a dictionary to a JSON or YAML file.

        Args:
            path: Path to a JSON/YAML file to save.
            data: A dictionary to save.
            comments: If not `None`, comments are added to a YAML file. Defaults to `None`.
            indent: The indentation level for a JSON/YAML file. Defaults to 2.
            file_permission: The permissions for a JSON/YAML file. Defaults to 644.
            dir_permission: The permissions for a parent directory of a JSON/YAML file. Defaults to 755.
            encoding: An encoding for a JSON/YAML file. Defaults to 'utf-8'.

        Raises:
            ValueError: If the file extension is not .json, .yaml, or .yml.
        """
        if cls.is_json(path):
            save_data_to_json(
                data=data,
                output_json_file=path,
                indent=indent,
                file_permission=file_permission,
                dir_permission=dir_permission,
                encoding=encoding,
            )
        elif cls.is_yaml(path):
            save_data_to_yaml_with_comments(
                data=data,
                output_yaml_file=path,
                comment_dict=comments,
                indent=indent,
                file_permission=file_permission,
                dir_permission=dir_permission,
                encoding=encoding,
            )
        else:
            raise ValueError(
                f"Unsupported file format: '{path.suffix}'. "
                "StructuredDataIO only supports JSON (.json) and YAML (.yaml, .yml)."
            )

    @classmethod
    def load(cls, path: Path, *, encoding: str = "utf-8") -> dict[str, Any]:
        """Loads data from a JSON or YAML file.

        Args:
            path: Path to a JSON/YAML file to load.
            encoding: An encoding for a JSON/YAML file. Defaults to 'utf-8'.

        Returns:
            A structured data used for instantiation of the relevant class.

        Raises:
            ValueError: If the file extension is not .json, .yaml, or .yml.
        """
        if cls.is_json(path):
            return load_data_from_json(input_json_file=path, encoding=encoding)
        elif cls.is_yaml(path):
            return load_data_from_yaml(input_yaml_file=path, encoding=encoding)
        else:
            raise ValueError(
                f"Unsupported file format: '{path.suffix}'. "
                "StructuredDataIO only supports JSON (.json) and YAML (.yaml, .yml)."
            )

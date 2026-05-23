from pathlib import Path

from pydantic import BaseModel

from simple_experiment_manager.api import experiment as api_experiment
from simple_experiment_manager.api import index as api_index
from simple_experiment_manager.api import label as api_label
from simple_experiment_manager.schemas import requests as req_schemas
from simple_experiment_manager.schemas import responses as res_schemas
from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext
from simple_experiment_manager.schemas.enums import ExperimentSortKey
from simple_experiment_manager.schemas.index import ExperimentIndex, ExperimentMetadata
from simple_experiment_manager.schemas.status import OperationStatus


class ExperimentManager:
    """The main API for managing experiments and their configurations.

    This class orchestrates experiment creation, indexing, and label management
    by delegating business logic to specialized API functions.
    """

    # Internal states
    def __init__(self, ctx: ExperimentContext) -> None:
        """Initializes the manager with a experiment context."""
        self.ctx: ExperimentContext = ctx
        self._index: ExperimentIndex | None = None
        self.refresh()

    def _update_state(self, response: res_schemas.ExperimentManagerResponse) -> None:
        """Updates the internal state with the given response."""
        if response.is_success and response.current_index:
            self._index = response.current_index

    def refresh(self) -> None:
        """Gets the current index and updates the internal state."""
        req = req_schemas.RequestGetIndex()
        res = api_index.get_index(request=req, context=self.ctx)
        self._update_state(res)

    def _resolve_target_experiment(self, name: str | None) -> str:
        """Returns the experiment name if provided, otherwise the name of the active experiment."""
        target = name or self.active_experiment
        if target is None:
            raise ValueError(
                "No experiment name provided and no active experiment is set."
            )

        if target not in self.experiments:
            raise ValueError(f"Experiment not found: {target}")
        return target

    # properties
    @property
    def project_name(self) -> str:
        """Returns the project name, derived from the base directory in the experiment context."""
        return self.ctx.project_name

    @property
    def experiment_root(self) -> Path:
        """Provides the experiment root path."""
        return self.ctx.experiment_root

    @property
    def experiment_index_file(self) -> Path:
        """Provides the path to the experiment index file."""
        return self.ctx.experiment_index_file

    @property
    def index(self) -> ExperimentIndex:
        """Provides the current `ExperimentIndex` instance. Returns `None` if not yet loaded."""
        # try to refresh
        if self._index is None:
            self.refresh()

        # validate the internal index object
        if self._index is None:
            raise RuntimeError(
                "ExperimentIndex could not be initialized. This indicates a failure in the "
                "underlying storage or a critical error in the refresh process."
            )
        return self._index

    @property
    def experiments(self) -> list[str]:
        """Gets the set of all registered experiment names."""
        return list(self.index.experiments.keys())

    @property
    def global_labels(self) -> list[str]:
        """Gets the list of labels defined at the global level."""
        return self.index.global_labels

    @property
    def active_experiment(self) -> str | None:
        """Gets the name of the currently active experiment, if it is set."""
        return self.index.active_experiment

    @property
    def active_experiment_metadata(self) -> ExperimentMetadata | None:
        """Gets the metadata for the active experiment.

        Returns None if no active experiment is set.
        """
        _, meta = self.get_experiment_metadata()
        return meta

    @property
    def active_experiment_dir(self) -> Path | None:
        """Gets the directory path for the active experiment.

        Returns None if no active experiment is set.
        """
        _, dir_path = self.get_experiment_dir()
        return dir_path

    @property
    def active_experiment_config_file(self) -> Path | None:
        """Gets the configuration file path for the active experiment.

        Returns None if no active experiment is set.
        """
        _, config_path = self.get_experiment_config_file()
        return config_path

    # operation methods
    def create_experiment(
        self,
        name: str | None = None,
        config: BaseModel | ConfigClass | None = None,
        description: str = "",
        dir_name: str | None = None,
    ) -> OperationStatus:
        """Creates a new experiment directory and initializes its configuration file.

        Args:
            name: A unique name for the experiment (logical name).
                If None, the directory name is assigned as the experiment name. Defaults to None.
            config: An instance of the configuration which must match the type of ctx.default_config.
                If None, default_config is used. Defaults to None.
            description: A brief summary for the experiment to create. Defaults to the empty string.
            dir_name: The actual directory name to create (physical name).
                If None, automatically assigned (e.g., 'exp_001'). Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.create_experiment()`.
        """
        req = req_schemas.RequestCreateExperiment(
            experiment_name=name,
            dir_name=dir_name,
            config=config,
            description=description,
        )
        res = api_experiment.create_experiment(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def set_active_experiment(self, name: str) -> OperationStatus:
        """Switches the active experiment.

        Args:
           name: A experiment name to be active.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.set_active_experiment()`.
        """
        req = req_schemas.RequestSetActiveExperiment(experiment_name=name)
        res = api_experiment.set_active_experiment(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def unset_active_experiment(self) -> OperationStatus:
        """Unsets the active experiment."""
        req = req_schemas.RequestSetActiveExperiment(experiment_name=None)
        res = api_experiment.set_active_experiment(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def delete_experiment(self, name: str) -> OperationStatus:
        """Deletes the experiment directory and removes it from the index.

        If the deleted experiment is set to be active, `active_experiment` in the index is set to `None`.

        Args:
           name: A experiment name to delete.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.delete_experiment()`.
        """
        req = req_schemas.RequestDeleteExperiment(experiment_name=name)
        res = api_experiment.delete_experiment(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def copy_experiment(
        self,
        src_name: str,
        dst_name: str,
        dst_dir_name: str | None = None,
        description: str | None = None,
    ) -> OperationStatus:
        """Creates a new experiment by copying the existing experiment.

        Args:
            src_name: The experiment name to copy from.
            dst_name: The experiment name to copy to.
            dst_dir_name: The actual directory name to create by copy.
            If None, automatically assigned, such as 'exp_001'. Defaults to None.
            description: A new description. If None, copies from the source experiment.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.copy_experiment()`.
        """
        req = req_schemas.RequestCopyExperiment(
            src_experiment_name=src_name,
            dst_experiment_name=dst_name,
            dst_dir_name=dst_dir_name,
            description=description,
        )
        res = api_experiment.copy_experiment(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def update_experiment_config(
        self, config: BaseModel | ConfigClass, name: str | None = None
    ) -> OperationStatus:
        """Updates the configuration for a experiment.

        Args:
            config: The new experiment configuration matching the type of context's `default_config`.
            name: The name of the experiment to update. If None, the active experiment is chosen. Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.update_experiment_config()`.
        """
        try:
            target_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestUpdateExperimentConfig(
                experiment_name=target_name, config=config
            )
            res = api_experiment.update_experiment_config(request=req, context=self.ctx)
            self._update_state(res)
            return OperationStatus(is_success=res.is_success, message=res.message)
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e))

    def rename_experiment(
        self,
        new_name: str,
        old_name: str | None = None,
    ) -> OperationStatus:
        """Renames the experiment name.

        Args:
            new_name: The new experiment name.
            old_name: The old experiment name. If None, the active experiment. Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.rename_experiment()`.
        """
        try:
            target_old_name = self._resolve_target_experiment(old_name)
            req = req_schemas.RequestRenameExperiment(
                old_experiment_name=target_old_name, new_experiment_name=new_name
            )
            res = api_experiment.rename_experiment(request=req, context=self.ctx)
            self._update_state(res)
            return OperationStatus(is_success=res.is_success, message=res.message)
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e))

    def get_experiment_config(
        self, name: str | None = None
    ) -> tuple[OperationStatus, BaseModel | ConfigClass | None]:
        """Retrieves the configuration for a experiment.

        Args:
            name: The experiment name whose configuration is to be retrieved.
            If None, the active experiment. Defaults to None.

        Returns:
            A tuple of (An `OperationStatus` instance, config).
            It can be unpacked as `(ok, msg), config = manager.get_experiment_config()`.
        """
        try:
            target_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestGetExperimentConfig(experiment_name=target_name)
            res = api_experiment.get_experiment_config(request=req, context=self.ctx)
            status = OperationStatus(is_success=res.is_success, message=res.message)
            return status, res.config
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e)), None

    def filter_experiments(
        self,
        labels: list[str] | None = None,
        sort_by: str = ExperimentSortKey.NAME.value,
        reverse: bool = False,
    ) -> tuple[OperationStatus, list[str]]:
        """Filters and sorts experiments.

        Args:
            labels: A list of labels to filter experiments. If None, label filtering is skipped. Defaults to None.
            sort_by: Sort key.　Available keys are defined by `ExperimentSortKey`. Defaults to `ExperimentSortKey.NAME.value`.
            reverse: If True, sorted by the descending order. Defaults to False.

        Returns:
            A tuple of (An `OperationStatus` instance, experiments).
            It can be unpacked as `(ok, msg), experiments = manager.filter_experiments()`.
        """
        try:
            sort_by_enum = ExperimentSortKey(sort_by)
        except ValueError:
            valid_keys = [e.value for e in ExperimentSortKey]
            status = OperationStatus(
                is_success=False,
                message=f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(valid_keys)}",
            )
            return status, []

        req = req_schemas.RequestFilterExperiments(
            labels=labels, sort_by=sort_by_enum, reverse=reverse
        )
        res = api_experiment.filter_experiments(request=req, context=self.ctx)
        status = OperationStatus(is_success=res.is_success, message=res.message)
        return status, res.experiments

    def add_labels_to_experiment(
        self,
        labels: list[str],
        name: str | None = None,
    ) -> OperationStatus:
        """Adds labels to the experiment and ensures they are registered in the global label list.

        Args:
           labels: A list of label names to add.
           name: The experiment name to add labels to. If None, the active experiment name. Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.add_labels_to_experiment()`.
        """
        try:
            target_experiment_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestAddLabelsToExperiment(
                labels=labels,
                experiment_name=target_experiment_name,
            )
            res = api_label.add_labels_to_experiment(request=req, context=self.ctx)
            self._update_state(res)
            return OperationStatus(is_success=res.is_success, message=res.message)
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e))

    def remove_global_labels(self, labels: list[str]) -> OperationStatus:
        """Removes multiple labels from the global label list and from all the experiments.

        Args:
           labels: A list of label names to remove from the global label list.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.remove_global_lables()`.
        """
        req = req_schemas.RequestRemoveGlobalLabels(labels=labels)
        res = api_label.remove_global_labels(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def rename_global_label(self, old_name: str, new_name: str) -> OperationStatus:
        """Renames a global label and updates its usage across all experiments.

        Args:
            old_name: The current name of the label to change.
            new_name: The new name for the label.

        Returns:
            An `OperationStatus` instance.
            It can be unpacked as `ok, msg = manager.rename_global_label()`.
        """
        req = req_schemas.RequestRenameGlobalLabel(
            old_label_name=old_name, new_label_name=new_name
        )
        res = api_label.rename_global_label(request=req, context=self.ctx)
        self._update_state(res)
        return OperationStatus(is_success=res.is_success, message=res.message)

    def update_experiment_labels(
        self,
        labels: list[str],
        name: str | None = None,
    ) -> OperationStatus:
        """Updates labels for a experiment.

        Args:
           labels: A list of label names to assign. All labels must already exist in the global label　list.
           name: The name of the experiment whose labels will be updated. If None, the active experiment. Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.update_experiment_labels()`.
        """
        try:
            target_experiment_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestUpdateExperimentLabels(
                experiment_name=target_experiment_name, labels=labels
            )
            res = api_label.update_experiment_labels(request=req, context=self.ctx)
            self._update_state(res)
            return OperationStatus(is_success=res.is_success, message=res.message)
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e))

    def update_experiment_description(
        self, description: str, name: str | None = None
    ) -> OperationStatus:
        """Updates the description for the specified experiment.

        Args:
            description: A new description for the experiment.
            name: The name of the experiment to update. If None, the active experiment is chosen. Defaults to None.

        Returns:
            An `OperationStatus` instance. It can be unpacked as `ok, msg = manager.update_experiment_description()`.
        """
        try:
            target_experiment_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestUpdateExperimentDescription(
                experiment_name=target_experiment_name, description=description
            )
            res = api_experiment.update_experiment_description(
                request=req, context=self.ctx
            )
            self._update_state(res)
            return OperationStatus(is_success=res.is_success, message=res.message)
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e))

    def get_label_usage(self) -> tuple[OperationStatus, dict[str, list[str]]]:
        """Gets the label usage, providing a mapping of the labels to the sets of experiment names that use them.

        Returns:
            A tuple of (An `OperationStatus` instance, usage_dict).
            It can be unpacked as `(ok, msg), usage = manager.get_label_usage()`.
        """
        req = req_schemas.RequestGetLabelUsage()
        res = api_label.get_label_usage(request=req, context=self.ctx)
        status = OperationStatus(is_success=res.is_success, message=res.message)
        return status, res.usage

    def get_experiment_label_map(
        self, name: str | None = None
    ) -> tuple[OperationStatus, dict[str, bool] | None]:
        """Gets a map of all global labels and whether they are assigned to the specified experiment.

        Args:
            name: The experiment name to acquire the label map. If None, the active experiment. Defaults to None.

        Returns:
            A tuple of (An `OperationStatus` instance, label_map).
            It can be unpacked as `(ok, msg), label_map = manager.get_label_map()`.
        """
        try:
            target_name = self._resolve_target_experiment(name)
            req = req_schemas.RequestGetExperimentLabelMap(experiment_name=target_name)
            res = api_label.get_experiment_label_map(request=req, context=self.ctx)
            return OperationStatus(
                is_success=res.is_success, message=res.message
            ), res.label_map
        except ValueError as e:
            return OperationStatus(is_success=False, message=str(e)), None

    # information access methods
    def get_experiment_metadata(
        self, name: str | None = None
    ) -> tuple[OperationStatus, ExperimentMetadata | None]:
        """Gets the metadata for the specified experiment or the active experiment.

        Args:
            name: The experiment name. If None, the active experiment is chosen. Defaults to None.

        Returns:
            A tuple of (An `OperationStatus` instance, metadata).
            It can be unpacked as `(ok, msg), meta = manager.get_experiment_metadata()`.
        """
        try:
            target = self._resolve_target_experiment(name)
            status = OperationStatus(
                is_success=True,
                message="Successfully retrieved the experiment metadata.",
            )
            meta = self.index.get_experiment_metadata(target)
            return status, meta
        except ValueError as e:
            status = OperationStatus(is_success=False, message=str(e))
            return status, None

    def get_experiment_dir(
        self, name: str | None = None
    ) -> tuple[OperationStatus, Path | None]:
        """Gets the directory path for the specified experiment or the active experiment.

        Args:
            name: The experiment name. If None, the active experiment is chosen. Defaults to None.

        Returns:
            A tuple of (An `OperationStatus` instance, exp_dir_path).
            It can be unpacked as `(ok, msg), exp_dir_path = manager.get_experiment_dir()`.
        """
        try:
            target = self._resolve_target_experiment(name)
            status = OperationStatus(
                is_success=True,
                message="Successfully retrieved the experiment directory path.",
            )
            dir_path = self.index.get_experiment_dir(
                root=self.experiment_root, experiment_name=target
            )
            return status, dir_path
        except ValueError as e:
            status = OperationStatus(is_success=False, message=str(e))
            return status, None

    def get_experiment_config_file(
        self, name: str | None = None
    ) -> tuple[OperationStatus, Path | None]:
        """Gets the configuration file path for the specified experiment or the active experiment.

        Args:
            name: The experiment name. If None, the active experiment is chosen. Defaults to None.

        Returns:
            A tuple of (An `OperationStatus` instance, config_file_path).
            It can be unpacked as `(ok, msg), config_file_path = manager.get_config_file()`.
        """
        try:
            target = self._resolve_target_experiment(name)
            status = OperationStatus(
                is_success=True,
                message="Successfully retrieved the configuration path.",
            )
            config_path = self.index.get_experiment_config(
                root=self.experiment_root, experiment_name=target
            )
            return status, config_path
        except ValueError as e:
            status = OperationStatus(is_success=False, message=str(e))
            return status, None

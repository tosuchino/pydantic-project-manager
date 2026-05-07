from typing import Any

from pydantic import BaseModel

from simple_experiment_manager.io.handlers import ExperimentDataIO
from simple_experiment_manager.schemas import requests as req_schemas
from simple_experiment_manager.schemas import responses as res_schemas
from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext
from simple_experiment_manager.schemas.index import ExperimentIndex, ExperimentMetadata


def create_experiment(
    request: req_schemas.RequestCreateExperiment, context: ExperimentContext
) -> res_schemas.ResponseCreateExperiment:
    io = ExperimentDataIO(context)

    try:
        actual_config = request.config
        if not actual_config:
            default_config = context.default_config
            if isinstance(default_config, BaseModel):
                actual_config = default_config.model_copy(deep=True)
            else:
                actual_config = ConfigClass(**default_config.to_dict())

        # experiment directory name and identifier
        dir_name = request.dir_name or _generate_next_experiment_dir_name(context)
        experiment_name = request.experiment_name or dir_name

        updated_index = _create_experiment_core(
            experiment_name=experiment_name,
            dir_name=dir_name,
            config=actual_config,
            context=context,
            io=io,
            description=request.description,
        )

        return res_schemas.ResponseCreateExperiment(
            is_success=True,
            message=f"Experiment '{experiment_name}' created.",
            current_index=updated_index,
        )

    except Exception as e:
        return res_schemas.ResponseCreateExperiment(is_success=False, message=str(e))


def set_active_experiment(
    request: req_schemas.RequestSetActiveExperiment, context: ExperimentContext
) -> res_schemas.ResponseSetActiveExperiment:
    """Sets or unsets the active experiment in the index."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        target = request.experiment_name

        if target is not None:
            # set the active experiment
            # validate the experiment existence
            if target not in index.experiments:
                return res_schemas.ResponseSetActiveExperiment(
                    is_success=False,
                    message=f"Experiment '{target}' does not exist.",
                )
            message = f"Experiment '{target}' is now active."
        else:
            # unset the active experiment
            message = "Active experiment has been unset."

        # update the active experiment
        index.active_experiment = target
        io.save_index(index)

        return res_schemas.ResponseSetActiveExperiment(
            is_success=True,
            message=message,
            current_index=index,
        )
    except Exception as e:
        return res_schemas.ResponseSetActiveExperiment(is_success=False, message=str(e))


def delete_experiment(
    request: req_schemas.RequestDeleteExperiment, context: ExperimentContext
) -> res_schemas.ResponseDeleteExperiment:
    """Permanently deletes the experiment directory and its metadata from the index."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        experiment_name = request.experiment_name

        # retrieve the experiment directory path
        target_dir = index.get_experiment_dir(
            root=context.experiment_root, experiment_name=experiment_name
        )

        # delete the experiment directory
        io.delete_experiment_data(target_dir)

        # remove the experiment from the index
        del index.experiments[experiment_name]

        # reset the active experiment if it is removed
        if index.active_experiment == experiment_name:
            index.active_experiment = None

        io.save_index(index)
        return res_schemas.ResponseDeleteExperiment(
            is_success=True,
            message=f"Experiment '{request.experiment_name}' deleted.",
            current_index=index,
        )
    except Exception as e:
        return res_schemas.ResponseDeleteExperiment(is_success=False, message=str(e))


def copy_experiment(
    request: req_schemas.RequestCopyExperiment, context: ExperimentContext
) -> res_schemas.ResponseCopyExperiment:
    """Creates a new experiment by copying another existing experiment config."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        src_experiment_name = request.src_experiment_name
        dst_experiment_name = request.dst_experiment_name

        # validate experiment existence
        if src_experiment_name not in index.experiments:
            return res_schemas.ResponseCopyExperiment(
                is_success=False,
                message=f"Experiment '{src_experiment_name}' does not exist.",
            )

        # retrieve the souce metadata
        meta = index.get_experiment_metadata(src_experiment_name)

        config_file = index.get_experiment_config(
            root=context.experiment_root, experiment_name=src_experiment_name
        )
        src_config = io.load_config(config_file)

        src_labels = meta.labels
        new_description = request.description or meta.description

        # determine destination experiment directory name
        dst_dir_name = request.dst_dir_name or _generate_next_experiment_dir_name(
            context
        )

        updated_index = _create_experiment_core(
            experiment_name=dst_experiment_name,
            dir_name=dst_dir_name,
            config=src_config,
            context=context,
            io=io,
            labels=src_labels,
            description=new_description,
        )
        return res_schemas.ResponseCopyExperiment(
            is_success=True,
            message=f"Copied from '{src_experiment_name}' to '{dst_experiment_name}'.",
            current_index=updated_index,
        )
    except Exception as e:
        return res_schemas.ResponseCopyExperiment(is_success=False, message=str(e))


def update_experiment_config(
    request: req_schemas.RequestUpdateExperimentConfig, context: ExperimentContext
) -> res_schemas.ResponseUpdateExperimentConfig:
    """Updates the configuration file of an existing experiment."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        experiment_name = request.experiment_name

        # validate config type matching
        _validate_config_type(config=request.config, ctx=context)

        # retrieve the configuration file path
        config_file = index.get_experiment_config(
            root=context.experiment_root, experiment_name=experiment_name
        )

        # save the updated config
        io.save_config(path=config_file, config=request.config)

        return res_schemas.ResponseUpdateExperimentConfig(
            is_success=True,
            message=f"Configuration for '{request.experiment_name}' updated successfully.",
            current_index=index,
        )
    except Exception as e:
        return res_schemas.ResponseUpdateExperimentConfig(
            is_success=False, message=str(e)
        )


def update_experiment_description(
    request: req_schemas.RequestUpdateExperimentDescription, context: ExperimentContext
) -> res_schemas.ResponseUpdateExperimentDescription:
    """Updates the description for the specified experiment."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        experiment_name = request.experiment_name

        # validate experiment existence
        if experiment_name not in index.experiments:
            return res_schemas.ResponseUpdateExperimentDescription(
                is_success=False, message=f"Experiment '{experiment_name}' not found."
            )

        # update description
        new_description = request.description
        meta = index.get_experiment_metadata(experiment_name)
        meta.description = new_description

        # save the index
        io.save_index(index)

        return res_schemas.ResponseUpdateExperimentDescription(
            is_success=True,
            message=f"Description for the experiment '{experiment_name}' updated to: {new_description}",
            current_index=index,
        )

    except Exception as e:
        return res_schemas.ResponseUpdateExperimentDescription(
            is_success=False, message=str(e)
        )


def rename_experiment(
    request: req_schemas.RequestRenameExperiment, context: ExperimentContext
) -> res_schemas.ResponseRenameExperiment:
    """Renames the experiment."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        old_experiment_name = request.old_experiment_name
        new_experiment_name = request.new_experiment_name

        # validate experiment existence
        if old_experiment_name not in index.experiments:
            return res_schemas.ResponseRenameExperiment(
                is_success=False,
                message=f"Experiment '{old_experiment_name}' not found.",
            )

        # pop the old metadata and re-assign to the new key
        metadata = index.experiments.pop(old_experiment_name)
        index.experiments[request.new_experiment_name] = metadata

        # update active experiment if necessary
        if index.active_experiment == old_experiment_name:
            index.active_experiment = new_experiment_name

        # save updated index
        io.save_index(index)

        return res_schemas.ResponseRenameExperiment(
            is_success=True,
            message=f"Experiment '{request.old_experiment_name}' renamed to '{request.new_experiment_name}'.",
            current_index=index,
        )
    except Exception as e:
        return res_schemas.ResponseRenameExperiment(is_success=False, message=str(e))


def get_experiment_config(
    request: req_schemas.RequestGetExperimentConfig, context: ExperimentContext
) -> res_schemas.ResponseGetExperimentConfig:
    """Retrieves the configuration instance for a specified experiment."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        config_file = index.get_experiment_config(
            root=context.experiment_root, experiment_name=request.experiment_name
        )
        config = io.load_config(config_file)
        return res_schemas.ResponseGetExperimentConfig(
            is_success=True,
            message=f"Configuration for experiment '{request.experiment_name}' successfully retrieved.",
            current_index=index,
            config=config,
        )
    except Exception as e:
        return res_schemas.ResponseGetExperimentConfig(is_success=False, message=str(e))


def filter_experiments(
    request: req_schemas.RequestFilterExperiments, context: ExperimentContext
) -> res_schemas.ResponseFilterExperiments:
    """Filters experiments based on specified criteria."""
    io = ExperimentDataIO(context)
    try:
        index = io.load_index()
        all_experiments = index.experiments
        # label filter
        target_labels = request.labels
        if target_labels is not None:
            target_set = set(target_labels)
            label_filtered = {
                name: meta
                for name, meta in all_experiments.items()
                if target_set.issubset(set(meta.labels))
            }
        else:
            label_filtered = all_experiments.copy()
        return res_schemas.ResponseFilterExperiments(
            is_success=True,
            message="Experiments have been successfully filtered.",
            experiments=list(label_filtered.keys()),
        )
    except Exception as e:
        return res_schemas.ResponseFilterExperiments(
            is_success=False, message=str(e), experiments=None
        )


# helper functions


def _create_experiment_core(
    experiment_name: str,
    dir_name: str,
    config: BaseModel | ConfigClass,
    context: ExperimentContext,
    io: ExperimentDataIO,
    labels: list[str] | None = None,
    description: str = "",
) -> ExperimentIndex:
    """Creates a experiment configuration and updates the experiment index after validation.

    This internal function handles shared logic for both `create` and `copy` operations.

    Args:
        experiment_name: The identifier for the new experiment.
        dir_name: The experiment directory name to create.
        config: The experiment configuration instance which matches the context's `default_config`.
        context: The experiment context.
        io: The experiment data IO handler.
        labels: A list of label names to add. If None, an empty list is used. Defaults to None.
        description: A description for the experiment. Defaults to the empty string.

    Returns:
        The updated `ExperimentIndex` instance.

    Raises:
        - FileExistsError: If a experiment directory having `experiment_name` already exists.
    """
    experiment_dir = context.get_experiment_dir(dir_name)
    config_file = context.get_config_file_from_dir(dir_name)

    # validate config type
    _validate_config_type(config=config, ctx=context)

    # validate experiment directory existence
    if experiment_dir.exists():
        raise FileExistsError(
            f"Experiment directory already exists: {experiment_dir.name}"
        )

    index = io.load_index()

    # validate experiment name existence
    if experiment_name in index.experiments:
        raise ValueError(f"Experiment name '{experiment_name}' is already taken.")

    # save config file
    io.save_config(path=config_file, config=config)

    # update index file
    labels = labels if labels else list()
    index.experiments[experiment_name] = ExperimentMetadata(
        labels=labels,
        relative_config_path=config_file.relative_to(context.experiment_root),
        description=description,
    )
    index.active_experiment = experiment_name
    io.save_index(index)

    return index


def _validate_config_type(config: Any, ctx: ExperimentContext) -> None:
    "Validates the type of `config` based on the experiment context."
    expected = ctx.default_config

    if isinstance(expected, BaseModel):
        if not isinstance(config, BaseModel):
            raise TypeError(
                f"Expected {type(expected).__name__}, got {type(config).__name__}"
            )
    elif isinstance(expected, ConfigClass):
        if not isinstance(config, ConfigClass):
            raise TypeError(f"Expected `ConfigClass`, got {type(config).__name__}")


def _generate_next_experiment_dir_name(ctx: ExperimentContext) -> str:
    "Generates the next available experiment directory name."

    def gen_dir_name(prefix: str, digits: int, num: int) -> str:
        return f"{prefix}{str(num).zfill(digits)}"

    prefix = ctx.experiment_dir_prefix
    digits = ctx.experiment_dir_digits
    experiment_root = ctx.experiment_root

    if not experiment_root.exists():
        return gen_dir_name(prefix=prefix, digits=digits, num=1)

    existing_dirs = {d.name for d in experiment_root.iterdir() if d.is_dir()}

    for n in range(1, 10**digits):
        dir_name = gen_dir_name(prefix=prefix, digits=digits, num=n)
        if dir_name not in existing_dirs:
            return dir_name

    raise RuntimeError(
        f"No available directory names with prefix '{prefix}' and {digits} digits. "
        "Please increase 'experiment_dir_digits' in ExperimentContext or manually specify a directory name."
    )

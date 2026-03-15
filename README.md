# Simple Experiment Manager

A simple experiment management framework to handle experiment-specific configurations with an integrated CLI and APIs.

## 🌟 Features

- **Flexible Configuration**: Define your experiment configuration by keyword arguments or your Pydantic model.
- **Smart CLI**: Auto-generated YAML templates with comment-based help.
- **Experiment Management**: Easily create, rename, copy, switch, show, and delete experiments.
- **Labeling System**: Organize experiments with global labels.

## 📦 Directory Structure

The manager organizes files under your base directory (default: `~/Documents/simple_experiment_manager`):

```text
Documents/
└── simple_experiment_manager/       # Project directory (base_dir)
    └── experiments/                 # Experiment root (experiment_root_name)
        ├── experiment_index.json    # Global experiment index and labels (index_file_name)
        ├── exp_001/          　　　　　　　# Individual physical experiment directory
        │   └── config.yaml          # Experiment-specific configuration
        └── exp_002/
            └── config.yaml
```

Note that experiments are managed by the corresponding logical names in the index file.

## 🛠 Installation

### Environment

- **Python**: 3.10+
- [**uv**](https://docs.astral.sh/uv/)

### Setup

```shell
# Install all dependencies
uv sync
```

## 🚀 Quick start

### 1. Setup the Context

Setup your experiment context, please refer to [Data Structure](#-data-structure) for details.

```python
from pathlib import Path

from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext

default_config = ConfigClass(lr=1e-4, batch_size=32)
base_dir = Path.home() / "Documents" / "my_project" # experiment root is given by `base_dir / experiments`

experiment_ctx = ExperimentContext(
    default_config=default_config,
    base_dir=base_dir,
)
```

For details on the definition of experiment configuration, see [Default Configuration](#-default-configuration).

### 2. Use in Your Scripts (API)

The ExperimentManager provides a high-level API to access experiment data and paths. Please refer to [Core API](#-core-api) for details.

```python
from simple_experiment_manager.manager import ExperimentManager

manager = ExperimentManager(experiment_ctx)

# --- Operation Example ---
# Methods return an `OperationStatus` object. 
# You can check success and print a concise summary.
status = manager.create_experiment(name="baseline")
print(status.summary)  # e.g., "Success: Experiment 'baseline' created."

# --- Retrieval Example ---
# Retrieval methods return a tuple: (OperationStatus, Data)
status, config = manager.get_experiment_config()
if status.is_success:
    # Use the config object (Pydantic model or ConfigClass)
    print(f"Loaded config: {config}")
else:
    print(f"Error: {status.message}")

# --- Unpacking Style ---
# You can also unpack the nested status for even cleaner code
(ok, msg), usage = manager.get_label_usage()
if ok:
    print(usage)
```

For a comprehensive demonstration of API, checkout [examples/sample_script.py](src/simple_experiment_manager/examples/sample_script.py):

```shell
uv run python -m simple_experiment_manager.examples.sample_script
```

This generates the experiment index file (`experiment_index.json`) as:

```json
{
  "active_experiment": "tuned_v1",
  "global_labels": [
    "training",
    "cpu"
  ],
  "experiments": {
    "baseline": {
      "created_at": "2026-05-07T01:38:47.683077",
      "labels": [
        "training",
        "cpu"
      ],
      "relative_config_path": "exp_001/config.yaml",
      "description": "Finished training: accuracy reached 95%"
    },
    "tuned_v1": {
      "created_at": "2026-05-07T01:38:47.684580",
      "labels": [
        "training",
        "cpu"
      ],
      "relative_config_path": "exp_002/config.yaml",
      "description": "Updated learning rate for tuning"
    }
  }
}
```

and the configuration file (`exp_001/config.yaml`) as:

```yaml
lr: 0.0001
batch_size: 32
```

After testing the above sample script, please manually delete the sample project directory: `~/Documents/sample-simple-experiment-manager-script`

### 3. Integrate with CLI (Typer Example)

Integrate the provided `experiment_app` and `label_app` to your `Typer` instance.

```python
import typer
from simple_experiment_manager.manager import ExperimentManager
from simple_experiment_manager.cli.experiment import experiment_app
from simple_experiment_manager.cli.label import label_app

main_app = typer.Typer()
main_app.add_typer(experiment_app, name="experiment")
main_app.add_typer(label_app, name="label")

@main_app.callback()
def setup(ctx: typer.Context):
    # Initialize `ExperimentManager`, which provides the core API functions for experiment management.
    manager = ExperimentManager(experiment_ctx)
    # Inject the `ExperimentManager` instance into `ctx.obj` for use by subcommands.
    ctx.obj = {"experiment_manager": manager}

if __name__ == "__main__":
    main_app()
```

For a comprehensive demonstration of CLI, checkout [examples/sample_cli.py](src/simple_experiment_manager/examples/sample_cli.py):

```shell
uv run python -m simple_experiment_manager.examples.sample_cli --help
```

After testing the above sample script, please manually delete the sample project directory: `~/Documents/sample-simple-experiment-manager-cli`

## 📝 Reference

### 📋 Data Structure

`ExperimentContext` [[source]](src/simple_experiment_manager/schemas/contexts.py)

A configuration object required to initialize the `ExperimentManager`.

#### Parameters:

- default_config (BaseModel | ConfigClass): Your model for experiment settings.
- base_dir (Path): Parent directory of the experiment root (default: ~/Documents/simple_experiment_manager).
- experiment_root_name: Root directory name for experiments (default: experiments).
- config_file_name (str): Filename for experiment settings (default: config.yaml).
- index_file_name (str): Filename for the global index (default: experiment_index.json).

### 📝 Default Configuration

Users can define quickly the default configuration object by using `ConfigClass` as shown above:

```python
from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext

default_config = ConfigClass(lr=1e-4, batch_size=32)

experiment_ctx = ExperimentContext(default_config=default_config)
```

A `Pydantic` class is also available for the default configuration. The adoption of the `Pydantic` class provides auto validations and descriptions:

```python
from typing import Annotated

from pydantic import BaseModel, Field

from simple_experiment_manager.schemas.contexts import ExperimentContext

class MyConfig(BaseModel):
    lr: Annotated[float, Field(gt=0.0, description="learning rate")] = Field(default=1e-4)
    batch_size: Annotated[int, Field(gt=0, description="batch size")] = Field(default=32)

default_config = MyConfig()

experiment_ctx = ExperimentContext(default_config=default_config)
```

The config file is generated as follows:

```yaml
# learning rate
lr: 0.0001
# batch size
batch_size: 32
```

Note that the comments in the config yaml file are only added to top level fields.

### 📝 Core API

`ExperimentManager` [[source]](src/simple_experiment_manager/manager.py)

The primary interface for experiment operations.

#### Parameters:

- ctx (`ExperimentContext`): An instance of ExperimentContext defining the environment.

#### Properties

- `experiments`: `list[str]` of all registered logical experiment names.
- `global_labels`: `list[str]` of all registered global labels.
- `active_experiment`: Name of the active experiment (`str | None`).
- `active_experiment_metadata`: `ExperimentMetadata` for the active experiment.
- `active_experiment_dir`: The absolute `Path` to the active experiment directory.
- `active_experiment_config_file`: The absolute `Path` to the active experiment's config file.

#### Key Methods

**Note**: Most methods take an optional `name` argument. If `None`, the active experiment is targeted.

- `create_experiment(name, config, description, dir_name)`: Initializes a new experiment directory and config.
- `set_active_experiment(name)`: Set an active experiment.
- `unset_active_experiment(name)`: Unset the active experiment, as `None`.
- `delete_experiment(name)`: Deletes a experiment directory and removes it from the index.
- `copy_experiment(src_name, dst_name, dst_dir_name, description)`: Duplicates an existing experiment.
- `update_experiment_config(config, name)`: Updates the config of the specified experiment.
- `rename_experiment(new_name, old_name)`: Renames the logical experiment name.
- `get_experiment_config(name)`: Returns the validated config instance of the specified experiment as a tuple (`OperationStatus`, config).
- `add_labels_to_experiment(labels, name)`: Adds a label list to the specified experiment, and then updates the global labels.
- `remove_global_labels(labels)`: Removes a label list from the global label list and from all the experiments.
- `update_experiment_labels(labels, name)`: Updates labels for the specified experiment.
- `update_experiment_description(description, name)`: Updates the description for the specified experiment.
- `get_label_usage()`: Returns a mapping of labels to the experiments using them as a tuple (`OperationStatus`, usage).
- `get_experiment_label_map(name)`: Gets a map of all global labels and whether they are assigned to the specified experiment as a tuple (`OperationStatus`, label_map).
- `get_experiment_metadata(name)`: Gets the metadata for the specified experiment.
- `get_experiment_dir(name)`: Gets the directory path for the specified experiment.
- `get_experiment_config_file(name)`: Gets the configuration file path for the specified experiment.

## 🛠 CLI Commands

### Experiment Management (experiment)

- **list**: List all experiments with their active status and labels.
- **create**: Create a new experiment (opens editor for configuration).
- **switch**: Set a specific experiment as the active one.
- **update**: Re-edit the active experiment's configuration in your editor.
- **show**: Display the active configuration with YAML syntax highlighting.
- **rename**: Rename an existing experiment.
- **copy**: Create a new experiment by copying an existing one.
- **delete**: Delete an experiment directory and its index entry.
- **describe**: Update a description for a specific experiment.

### Label Management (label)

- **list**: Show global labels and usage counts. Use --verbose to see experiment names.
- **add**: Register new labels to a specific experiment and globally.
- **assign**: Assign/unassign labels to the active experiment via a YAML-based checkbox editor.
- **remove**: Delete a label from the global list and all assigned experiments.

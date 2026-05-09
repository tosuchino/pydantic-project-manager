from pathlib import Path

from simple_experiment_manager.manager import ExperimentManager
from simple_experiment_manager.schemas.contexts import ConfigClass, ExperimentContext

# 1. Setup ExperimentContext
# Pydantic-based or ConfigClass are available to define the default configuration
default_config = ConfigClass(lr=1e-4, batch_size=32)
base_dir = Path.home() / "Documents" / "sample-simple-experiment-manager-script"

context = ExperimentContext(
    default_config=default_config,
    base_dir=base_dir,
)

# 2. Instantiate ExperimentManager
manager = ExperimentManager(context)


def main() -> None:
    # --- Create experiment ---
    print("\n--- Create a new experiment with logical name and description ---")
    status_create = manager.create_experiment(
        name="baseline", description="First run with default hyperparameters"
    )
    print(status_create.summary)

    # --- Usage of active type properties ---
    print("\n--- Check the active experiment status ---")
    if manager.active_experiment:
        print(f"Active Experiment: {manager.active_experiment}")
        print(f"Project Name     : {manager.project_name}")
        print(f"Experiment Dir   : {manager.active_experiment_dir}")
        print(f"Config File Path : {manager.active_experiment_config_file}")

        # retrieve metadata
        if meta := manager.active_experiment_metadata:
            print(f"Description      : {meta.description}")
            print(f"Created At       : {meta.created_at}")

    # --- Add labels ---
    print("\n--- Add labels to the experiment ---")
    status_labels = manager.add_labels_to_experiment(labels=["training", "cpu"])
    print(status_labels.summary)

    # --- Copy experiment ---
    # Copied from the src to dst experiment with a new description
    print("\n--- Copy an experiment with a new description ---")
    status_copy = manager.copy_experiment(
        src_name="baseline",
        dst_name="tuned_v1",
        description="Updated learning rate for tuning",
    )
    print(status_copy.summary)

    # --- Update experiment description ---
    print("\n--- Update experiment description ---")
    status_desc = manager.update_experiment_description(
        description="Finished training: accuracy reached 95%",
        name="baseline",
    )
    print(status_desc.summary)

    # --- Add labels to the copied experiment ---
    status_add_labels = manager.add_labels_to_experiment(labels=["tuned"])
    print(status_add_labels.summary)

    # --- Show the logical name list of experiments ---
    print("\n--- List all logical experiment names ---")
    print(f"Registered experiments: {manager.experiments}")

    # --- Show the filtered experiments ---
    target_labels = ["tuned"]
    status_filtered, filtered_experiments = manager.filter_experiments(target_labels)
    if not status_filtered.is_success:
        print(f"Error occurred: {status_filtered.summary}")
    elif not filtered_experiments:
        print(f"No experiments matched with the labels {target_labels}")
    else:
        print("\n--- List filtered logical experiment names ---")
        print(
            f"Filtered experiments matched with the labels {target_labels}: {filtered_experiments}"
        )

    # --- Show the statistics of the label usage ---
    print("\n--- Check label usage statistics ---")
    status_usage, label_usage = manager.get_label_usage()
    if status_usage.is_success:
        print(f"Global label usage: {label_usage}")

    print(
        f"\n[Cleanup Notice]\nAfter testing, manually delete the sample project directory: {manager.experiment_root.parent}"
    )


if __name__ == "__main__":
    main()

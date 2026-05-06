from conftest import DummyConfig

from simple_experiment_manager.manager import ExperimentManager
from simple_experiment_manager.schemas.contexts import ExperimentContext


def test_create_experiment_and_io_integrity(
    manager: ExperimentManager, dummy_ctx: ExperimentContext
) -> None:
    """Ensure that creating a experiment creates the directory and updates status."""
    # Arrange
    name = "io-test-experiment"
    config = DummyConfig(user_name="tester")

    # Act
    status = manager.create_experiment(name, config)

    # Assert
    assert status.is_success
    assert manager.active_experiment == name
    assert dummy_ctx.experiment_index_file.exists()


def test_create_experiment_duplicate_fails(manager: ExperimentManager) -> None:
    """Negative test for creating experiments with duplicate names."""
    # Arrange
    name = "duplicate"
    manager.create_experiment(name, DummyConfig())

    # Act
    status = manager.create_experiment(name, DummyConfig())

    # Assert
    assert status.is_success is False


def test_rename_active_experiment_consistency(manager: ExperimentManager) -> None:
    """Ensure renaming the active experiment updates both the experiment list and the active status."""
    # Arrange
    old_name = "old-name"
    new_name = "new-name"
    manager.create_experiment(old_name, DummyConfig())
    manager.set_active_experiment(old_name)

    # Act
    status = manager.rename_experiment(new_name)

    # Assert
    assert status.is_success
    assert new_name in manager.experiments
    assert old_name not in manager.experiments
    assert manager.active_experiment == new_name


def test_label_management_flow(manager: ExperimentManager) -> None:
    """Verify global label assignment and assignment validation."""
    # Arrange
    manager.create_experiment("label-test", DummyConfig())
    manager.set_active_experiment("label-test")
    manager.add_labels_to_experiment(["label1", "label2"])

    # Act: Positive
    status_ok = manager.update_experiment_labels(["label1"])

    # Assert
    assert status_ok.is_success
    assert manager.index is not None
    assert "label1" in manager.index.experiments["label-test"].labels
    assert "label2" not in manager.index.experiments["label-test"].labels

    # Act: Negative, check if an invalid is assigned
    status_fail = manager.update_experiment_labels(["invalid-label"])

    # Assert
    assert status_fail.is_success is False
    assert "invalid-label" in status_fail.message


def test_delete_active_experiment_cleanup(
    manager: ExperimentManager, dummy_ctx: ExperimentContext
) -> None:
    """Ensure deleting an active experiment removes the directory and resets the active status."""
    # Arrange
    name = "to-be-deleted"
    manager.create_experiment(name, DummyConfig())
    manager.set_active_experiment(name)

    # Act
    status = manager.delete_experiment(name)

    # Assert
    assert status.is_success
    assert name not in manager.experiments
    assert manager.active_experiment is None  # if the active experiment is reset
    assert not dummy_ctx.get_experiment_dir(
        name
    ).exists()  # if the directory is really removed

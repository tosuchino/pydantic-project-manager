import typer

from simple_experiment_manager.cli.editor import edit_label_map_via_editor
from simple_experiment_manager.cli.utils import (
    console,
    initialize_context,
    resolve_manager,
)
from simple_experiment_manager.manager import ExperimentManager

label_app = typer.Typer(help="Manage global labels and experiment assignments.")


@label_app.callback()
def callback(ctx: typer.Context) -> None:
    initialize_context(ctx)


@label_app.command(name="list")
def command_list_labels(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show experiment names using each label."
    ),
):
    """List global labels and their usage statistics."""
    manager: ExperimentManager = resolve_manager(ctx)
    status, label_usage = manager.get_label_usage()  # get label usage

    if not status.is_success:
        print(status.summary)
        return

    from rich.table import Table

    table = Table(title="Global Label Usage", header_style="bold magenta")
    table.add_column("Label", style="cyan")
    table.add_column("Usage Count", justify="right", style="green")

    if verbose:
        table.add_column("Experiments", style="yellow")

    for label, experiments in sorted(label_usage.items()):
        row = [label, str(len(experiments))]
        if verbose:
            row.append(", ".join(sorted(list(experiments))))
        table.add_row(*row)

    console.print(table)


@label_app.command(name="add")
def command_add_labels_to_active_experiment(
    ctx: typer.Context,
    labels: list[str] = typer.Argument(..., help="A list of labels to add."),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Target experiment name. If None, the active experiment is used.",
    ),
):
    """Adds labels to a specific experiment (defaults to active experiment)."""
    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.add_labels_to_experiment(name=name, labels=labels)
    print(status.summary)


@label_app.command(name="assign")
def command_assign_labels(
    ctx: typer.Context,
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Target experiment name. If None, the active experiment is used.",
    ),
):
    """Assign or unassign labels to an experiment using the default editor."""
    manager: ExperimentManager = resolve_manager(ctx)

    # gets the current label map
    status, label_map = manager.get_experiment_label_map(name)

    # retrive error
    if not status.is_success or label_map is None:
        print(status.summary)
        return

    # edits the label status
    edited_map = edit_label_map_via_editor(ctx=manager.ctx, label_map=label_map)

    # updates the labels
    selected_labels = [name for name, active in edited_map.items() if active]

    update_status = manager.update_experiment_labels(name=name, labels=selected_labels)
    print(update_status.summary)


@label_app.command(name="remove")
def command_remove_labels(
    ctx: typer.Context,
    labels: list[str] = typer.Argument(..., help="A list of label names to remove."),
):
    """Remove labels from the global label list and all experiments."""
    confirm = typer.confirm(
        f"Remove labels '{labels}' from the global list and all experiments?"
    )
    if not confirm:
        raise typer.Abort()

    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.remove_global_labels(labels)
    print(status.summary)

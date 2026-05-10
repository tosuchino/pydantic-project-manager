import typer
from pydantic import BaseModel
from rich.syntax import Syntax
from rich.table import Table

from simple_experiment_manager.cli.editor import (
    build_template_dict_from_config_class,
    edit_config_via_editor,
    generate_yaml_string,
)
from simple_experiment_manager.cli.utils import (
    console,
    initialize_context,
    resolve_manager,
)
from simple_experiment_manager.manager import ExperimentManager, OperationStatus
from simple_experiment_manager.schemas.contexts import ExperimentContext
from simple_experiment_manager.schemas.enums import ExperimentSortKey

experiment_app = typer.Typer(
    help="Manage experiments: create, list, delete and rename."
)


@experiment_app.callback()
def callback(ctx: typer.Context) -> None:
    initialize_context(ctx)


@experiment_app.command(name="list")
def command_list_experiment(
    ctx: typer.Context,
    target_labels: list[str] | None = typer.Option(
        None,
        "--label",
        help="Label to filter experiments. Can be specified multiple times.",
    ),
    sort_by: ExperimentSortKey = typer.Option(
        ExperimentSortKey.NAME, "--sort_by", help="Sort key."
    ),
    reverse: bool = typer.Option(
        False, "--reverse", help="Sort results in descending order."
    ),
):
    """Lists experiments of the project."""
    manager: ExperimentManager = resolve_manager(ctx)
    index = manager.index

    # early return for no experiments
    if not index.experiments:
        console.print("[yellow]No experiments registered yet.[/yellow]")
        return

    # filter and sort experiments
    status, experiment_names = manager.filter_experiments(
        labels=target_labels, sort_by=sort_by.value, reverse=reverse
    )

    # system error
    if not status.is_success:
        console.print(f"[bold red]Error:[/bold red] {status.summary}")
        return

    # no matching experiments
    if not experiment_names and target_labels is not None:
        console.print(
            f"[yellow]No experiments matched the labels: {', '.join(target_labels)}[/yellow]"
        )
        return

    # table configuration
    table = Table(
        title=f"Managed Experiments in [bold cyan]{manager.project_name}[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        box=None,
    )

    # column configuration
    table.add_column("Active", justify="center", style="green")
    table.add_column("Experiment Name (Logical)", style="cyan", no_wrap=True)
    table.add_column("Directory (Physical)", style="blue")
    table.add_column("Labels", style="yellow")
    table.add_column("Description", style="white", overflow="fold")
    table.add_column("Created At", style="dim", justify="right")

    # add experiment rows to the table
    for name in experiment_names:
        meta = index.get_experiment_metadata(name)

        # format experiment metadata
        is_active = (
            "[bold]*[/bold]" if name == manager.active_experiment else ""
        )  # active symbol
        labels = ", ".join(meta.labels) if meta.labels else "-"  # labels
        desc = meta.description if meta.description else "-"  # description
        created_str = meta.created_at.strftime("%Y-%m-%d %H:%M")  # datetime string

        # add formatted values
        table.add_row(
            is_active,
            name,
            meta.dir_name,
            labels,
            desc,
            created_str,
        )

    console.print(table)


@experiment_app.command(name="create")
def command_create_experiment(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Experiment name to create."),
    description: str = typer.Option(
        "",
        "--message",
        "-m",
        help="A brief summary for the experiment. Defaults to the empty string.",
    ),
) -> None:
    """Creates a new experiment."""
    # experiment context
    manager: ExperimentManager = resolve_manager(ctx)
    experiment_ctx: ExperimentContext = manager.ctx

    # validate experiment existence
    if name in manager.experiments:
        failed_status = OperationStatus(
            is_success=False, message=f"Experiment '{name}' already exists."
        )
        print(failed_status.summary)
        return

    # edit config instance via editor
    data = build_template_dict_from_config_class(experiment_ctx.default_config)
    config_inst = edit_config_via_editor(ctx=experiment_ctx, data=data)

    # run and show the result
    status = manager.create_experiment(
        name=name, config=config_inst, description=description
    )
    print(status.summary)


@experiment_app.command(name="rename")
def command_rename_experiment(
    ctx: typer.Context,
    old_name: str = typer.Argument(..., help="Current experiment name."),
    new_name: str = typer.Argument(..., help="New experiment name."),
):
    """Renames an existing experiment."""
    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.rename_experiment(old_name=old_name, new_name=new_name)
    print(status.summary)


@experiment_app.command(name="delete")
def command_delete_experiment(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Experiment name to delete."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete without confirmation."
    ),
):
    """Deletes a experiment and its directory."""
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete '{name}'?")
        if not confirm:
            raise typer.Abort()

    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.delete_experiment(name)
    print(status.summary)


@experiment_app.command(name="switch")
def command_switch_experiment(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="The experiment name to switch."),
):
    """Switches the active experiment."""
    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.set_active_experiment(name)
    print(status.summary)


@experiment_app.command(name="show")
def command_show_experiment(
    ctx: typer.Context,
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Target experiment name. If None, the active experiment is used.",
    ),
):
    """Shows the configuration for the active experiment."""
    manager: ExperimentManager = resolve_manager(ctx)
    status, config = manager.get_experiment_config(name)
    if status.is_success and config:
        if isinstance(config, BaseModel):
            data = config.model_dump(mode="json")
        else:
            data = config.to_dict(mode="json")
        exp_name = name or manager.active_experiment
        yaml_str = generate_yaml_string(ctx=manager.ctx, data=data)
        console.print(f"\n[bold cyan]Experiment:[/bold cyan] {exp_name}")
        console.print(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True))
    else:
        print(status.summary)


@experiment_app.command(name="update")
def command_update_experiment(
    ctx: typer.Context,
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Target experiment name. If None, the active experiment is used.",
    ),
):
    """Edits the active experiment's configuration."""
    manager: ExperimentManager = resolve_manager(ctx)
    status, config = manager.get_experiment_config(name)

    if not status.is_success or config is None:
        print(status.summary)
        return

    # update config via the editor
    data = build_template_dict_from_config_class(config)
    new_config = edit_config_via_editor(ctx=manager.ctx, data=data)

    update_status = manager.update_experiment_config(config=new_config, name=name)
    print(update_status.summary)


@experiment_app.command(name="copy")
def command_copy_experiment(
    ctx: typer.Context,
    src_name: str = typer.Argument(..., help="The experiment name to copy from."),
    dst_name: str = typer.Argument(..., help="The experiment name to copy to."),
    dst_dir_name: str | None = typer.Option(
        None,
        "--dir_name",
        help="The directory name of the experiment to newly create by copy. If None, automatically assigned. Defaults to None.",
    ),
    description: str | None = typer.Option(
        None,
        "--message",
        "-m",
        help="A new description. If None, copies from the source experiment. Defaults to None.",
    ),
):
    """Creates a new experiment by copying an existing one."""
    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.copy_experiment(
        src_name=src_name,
        dst_name=dst_name,
        dst_dir_name=dst_dir_name,
        description=description,
    )
    print(status.summary)


@experiment_app.command(name="describe")
def command_describe_experiment(
    ctx: typer.Context,
    description: str = typer.Argument(
        ..., help="New description summary for the experiment."
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Target experiment name. If None, the active experiment is used.",
    ),
):
    """Sets a brief summary or note for an experiment."""
    manager: ExperimentManager = resolve_manager(ctx)
    status = manager.update_experiment_description(description=description, name=name)
    print(status.summary)

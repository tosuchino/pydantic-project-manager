from typing import Final

import typer
from rich.console import Console

from simple_experiment_manager.manager import ExperimentManager
from simple_experiment_manager.schemas.enums import OutputLevel
from simple_experiment_manager.schemas.status import OperationStatus

console = Console()

MANAGER_ATTR: Final[str] = "experiment_manager"


def handle_result(
    level: OutputLevel,
    message: str,
    success_prefix: str = "Success",
    error_prefix: str = "Error",
    warning_prefix: str = "Warning",
    terminate_on_error: bool = True,
) -> None:
    """Handles the result message display by the use of `Rich`.

    Args:
        level: An `OutputLevel` instance.
        message: The message to display in console.
        success_prefix: Customized prefix for success messages. Defaults to "Success".
        error_prefix: Customized prefix for error messages. Defaults to "Error".
        warning_prefix: Customized prefix for warning messages. Defaults to "Warning".
        terminate_on_error: If `True`, the failure operation will be terminated. Defaults to `True`.
    """
    match level:
        case OutputLevel.SUCCESS:
            pre_msg = success_prefix
            color = "green"
        case OutputLevel.ERROR:
            pre_msg = error_prefix
            color = "red"
        case OutputLevel.WARNING:
            pre_msg = warning_prefix
            color = "yellow"

    full_msg = f"{pre_msg}: {message}" if message else pre_msg
    console.print(f"[{color}]{full_msg}[/{color}]")

    if level == OutputLevel.ERROR and terminate_on_error:
        raise typer.Exit(code=1)


def handle_result_from_operation_status(
    status: OperationStatus, terminate_on_error: bool = True
) -> None:
    """Handles the result message display by the use of `Rich`　specifically for an `OperationStatus` instance.

    Args:
        status: The `OperationStatus` instance from the manager operation.
        terminate_on_error: If `True`, the failure operation will be terminated. Defaults to `True`.
    """
    handle_result(
        level=status.level,
        message=status.message,
        terminate_on_error=terminate_on_error,
    )


def initialize_context(ctx: typer.Context) -> None:
    """Ensures that the Typer context object is initialized."""
    if ctx.obj is None:
        ctx.obj = {}


def resolve_manager(ctx: typer.Context) -> ExperimentManager:
    """Resolves the `ExperimentManager` instance from the `typer.Context`.

    `ctx.obj` must satisfy one of the following　conditions:
    - It is a `ExperimentManager` instance.
    - It is a dictionary containing the 'experiment_manager' key mapped to a `ExperimentManager` instance.
    - It is an object with a 'experiment_manager' attribute that is a `ExperimentManager` instance.

    Args:
        ctx: The `typer.Context` instance.

    Returns:
        The resolved `ExperimentManager` instance.

    Raises:
        RuntimeError: If `typer.Context` does not meet any of the conditions above.
    """
    obj = ctx.obj

    if isinstance(obj, ExperimentManager):
        return obj

    if isinstance(obj, dict):
        manager = obj.get(MANAGER_ATTR)
        if isinstance(manager, ExperimentManager):
            return manager

    manager = getattr(obj, MANAGER_ATTR, None)
    if isinstance(manager, ExperimentManager):
        return manager

    raise RuntimeError(
        f"Could not resolve ExperimentManager from {type(obj).__name__}."
        f"Please ensure `ctx.obj` or `ctx.obj.{MANAGER_ATTR}` is a `ExperimentManager` instance."
    )

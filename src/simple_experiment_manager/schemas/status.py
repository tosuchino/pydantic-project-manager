from typing import NamedTuple

from simple_experiment_manager.schemas.enums import OutputLevel


class OperationStatus(NamedTuple):
    """Represents the status and message of a manager operation."""

    is_success: bool
    message: str

    def to_summary(
        self, success_prefix: str = "Success", error_prefix: str = "Error"
    ) -> str:
        """Returns a customized summary message without any UI-specific formatting."""
        pre_msg = success_prefix if self.is_success else error_prefix
        if not self.message:
            return pre_msg
        return f"{pre_msg}: {self.message}"

    @property
    def summary(self) -> str:
        """Returns the default summarized message."""
        return self.to_summary()

    @property
    def level(self) -> OutputLevel:
        return OutputLevel.SUCCESS if self.is_success else OutputLevel.ERROR

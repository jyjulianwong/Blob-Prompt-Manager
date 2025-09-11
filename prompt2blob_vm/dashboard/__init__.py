"""Dashboard module for Prompt2Blob Version Manager."""

from prompt2blob_vm.dashboard.app import PromptDashboard
from prompt2blob_vm.dashboard.app import main as runner

__all__ = [
    "PromptDashboard",
    "runner",
]

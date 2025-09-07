"""Dashboard module for Blob Prompt Manager."""

from blob_prompt_manager.dashboard.app import PromptDashboard
from blob_prompt_manager.dashboard.app import main as runner

__all__ = [
    "PromptDashboard",
    "runner",
]

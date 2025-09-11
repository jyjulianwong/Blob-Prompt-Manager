#!/usr/bin/env python3
"""Demo script showing how to launch the dashboard programmatically."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from prompt2blob_vm.dashboard.runner import run_dashboard  # noqa: E402
from prompt2blob_vm.demo import DemoPromptManager  # noqa: E402


def runner_demo():
    """Launch the dashboard with DemoPromptManager."""
    print(
        "🚀 Launching Prompt2Blob Version Manager Dashboard with DemoPromptManager..."
    )

    # Initialize the DemoPromptManager
    demo_prompt_manager = DemoPromptManager(
        local_dir_path="prompts",
        gcs_bucket_name="bai-buchai-p-stb-usea1-creations",
        gcs_dir_path="tmp/prompt-artifacts/",
    )

    # Launch the dashboard
    run_dashboard(demo_prompt_manager, port=8501, host="localhost")


if __name__ == "__main__":
    runner_demo()

#!/usr/bin/env python3
"""Launcher script for the Prompt Manager Dashboard."""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from blob_prompt_manager.prompt_manager import PromptManager  # noqa: E402

# Global variable to store the prompt manager instance
_prompt_manager_instance = None


def run_dashboard(
    prompt_manager: PromptManager, port: int = 8501, host: str = "localhost"
):
    """Launch the dashboard with a specific PromptManager instance.

    Args:
        prompt_manager: The PromptManager instance to use in the dashboard
        port: Port to run the dashboard on (default: 8501)
        host: Host to run the dashboard on (default: localhost)
    """
    # Store the prompt manager instance globally so the Streamlit app can access it
    global _prompt_manager_instance
    _prompt_manager_instance = prompt_manager

    # Import Streamlit
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        print("Error: Streamlit is not installed. Please install it with:")
        print("pip install streamlit")
        sys.exit(1)

    # Set app file path
    app_file = project_root / "blob_prompt_manager" / "dashboard" / "app.py"
    print("🚀 Launching Blob Prompt Manager Dashboard...")
    print(f"🎯 Manager: {type(prompt_manager).__name__}")
    print(f"📁 Local Dir: {prompt_manager.local_dir_path}")
    if hasattr(prompt_manager, "gcs_bucket_name") and prompt_manager.gcs_bucket_name:
        print(f"☁️ GCS Bucket: {prompt_manager.gcs_bucket_name}")

    # Check if app file exists
    if not app_file.exists():
        print(f"Error: Dashboard file not found: {app_file}")
        sys.exit(1)

    print(f"📍 Dashboard will be available at: http://{host}:{port}")
    print("💡 Tip: Use Ctrl+C to stop the dashboard")

    # Launch Streamlit
    sys.argv = [
        "streamlit",
        "run",
        str(app_file),
        "--server.port",
        str(port),
        "--server.address",
        host,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    stcli.main()


def get_prompt_manager() -> Optional[PromptManager]:
    """Get the globally stored prompt manager instance.

    Returns:
        The PromptManager instance if available, None otherwise
    """
    return _prompt_manager_instance


def main():
    """Main launcher function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Launch the Prompt Manager Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py                    # Launch dashboard (requires prompt_manager parameter)
  python runner.py --port 8502        # Launch on custom port
  
Note: This script is primarily intended to be used programmatically.
For direct usage, use runner_demo.py instead.
        """,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run the dashboard on (default: 8501)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to run the dashboard on (default: localhost)",
    )

    # args = parser.parse_args()

    print("❌ Error: This script requires a PromptManager instance.")
    print(
        "💡 Use runner_demo.py for a working example, or call run_dashboard() programmatically."
    )
    print("")
    print("Example usage in code:")
    print("  from blob_prompt_manager.dashboard.runner import run_dashboard")
    print("  from blob_prompt_manager.examples import BrandMetricPromptManager")
    print("  ")
    print("  manager = BrandMetricPromptManager(local_dir_path='prompts')")
    print("  run_dashboard(manager, port=8501)")
    sys.exit(1)


if __name__ == "__main__":
    main()

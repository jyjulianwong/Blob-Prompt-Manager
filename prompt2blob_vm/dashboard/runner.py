#!/usr/bin/env python3
"""Launcher script for the Version Manager Dashboard."""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from prompt2blob_vm.version_manager import VersionManager  # noqa: E402

# Global variable to store the prompt manager instance
_prompt_manager_instance = None


def run_dashboard(
    version_manager: VersionManager, port: int = 8501, host: str = "localhost"
):
    """Launch the dashboard with a specific VersionManager instance.

    Args:
        version_manager: The VersionManager instance to use in the dashboard
        port: Port to run the dashboard on (default: 8501)
        host: Host to run the dashboard on (default: localhost)
    """
    # Store the prompt manager instance globally so the Streamlit app can access it
    global _prompt_manager_instance
    _prompt_manager_instance = version_manager

    # Import Streamlit
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        print("Error: Streamlit is not installed. Please install it with:")
        print("pip install streamlit")
        sys.exit(1)

    # Set app file path
    app_file = project_root / "prompt2blob_vm" / "dashboard" / "app.py"
    print("🚀 Launching Prompt2Blob Version Manager Dashboard...")
    print(f"🎯 Manager: {type(version_manager).__name__}")
    print(f"📁 Local Dir: {version_manager.local_dir_path}")
    if hasattr(version_manager, "gcs_bucket_name") and version_manager.gcs_bucket_name:
        print(f"☁️ GCS Bucket: {version_manager.gcs_bucket_name}")

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


def get_prompt_manager() -> Optional[VersionManager]:
    """Get the globally stored prompt manager instance.

    Returns:
        The VersionManager instance if available, None otherwise
    """
    return _prompt_manager_instance


def main():
    """Main launcher function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Launch the Version Manager Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py                    # Launch dashboard (requires version_manager parameter)
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

    print("❌ Error: This script requires a VersionManager instance.")
    print(
        "💡 Use runner_demo.py for a working example, or call run_dashboard() programmatically."
    )
    print("")
    print("Example usage in code:")
    print("  from prompt2blob_vm.dashboard.runner import run_dashboard")
    print("  from prompt2blob_vm.examples import BrandMetricPromptManager")
    print("  ")
    print("  manager = BrandMetricPromptManager(local_dir_path='prompts')")
    print("  run_dashboard(manager, port=8501)")
    sys.exit(1)


if __name__ == "__main__":
    main()

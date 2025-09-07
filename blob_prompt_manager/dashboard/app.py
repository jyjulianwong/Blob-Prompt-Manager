"""Streamlit dashboard for prompt management with comprehensive features."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import yaml
from streamlit_ace import st_ace

from blob_prompt_manager.dashboard.file_explorer import (
    GCSFileExplorer,
    LocalFileExplorer,
)
from blob_prompt_manager.prompt_manager import PromptManager


class PromptDashboard:
    """Comprehensive dashboard for prompt management with all features."""

    def __init__(self, prompt_manager: PromptManager):
        """Initialize the dashboard with a PromptManager instance.

        Args:
            prompt_manager: An instance of PromptManager or its subclasses
        """
        self.prompt_manager = prompt_manager
        self._init_session_state()
        self._init_file_explorers()

    def _init_session_state(self) -> None:
        """Initialize Streamlit session state variables."""
        defaults = {
            "selected_file": None,
            "selected_version": "local",
            "file_content": "",
            "gcs_configured": False,
            "show_file_tree": False,
            "search_query": "",
            "comparison_mode": False,
            "compare_version1": "local",
            "compare_version2": None,
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _init_file_explorers(self) -> None:
        """Initialize the file explorers based on the prompt manager configuration."""
        try:
            # Check if GCS is configured
            if (
                hasattr(self.prompt_manager, "gcs_bucket_name")
                and self.prompt_manager.gcs_bucket_name
                and hasattr(self.prompt_manager, "gcs_dir_path")
                and self.prompt_manager.gcs_dir_path
            ):
                st.session_state.gcs_configured = True
                self.gcs_explorer = GCSFileExplorer(self.prompt_manager)
            else:
                st.session_state.gcs_configured = False
                self.gcs_explorer = None

            # Initialize local explorer with the prompt manager's local directory
            local_dir = str(self.prompt_manager.local_dir_path)
            self.local_explorer = LocalFileExplorer(local_dir)

        except Exception as e:
            st.sidebar.error(f"Configuration error: {e}")
            self.gcs_explorer = None
            self.local_explorer = None

    def _render_sidebar_stats(self) -> None:
        """Render statistics in the sidebar."""
        if not self.local_explorer:
            return

        with st.sidebar:
            st.header("📊 Dashboard Statistics")

            # Show prompt manager info
            st.subheader("PromptManager Info")
            st.info(f"**Type:** {type(self.prompt_manager).__name__}")
            st.info(f"**Local Dir:** {self.prompt_manager.local_dir_path}")

            if st.session_state.gcs_configured:
                st.info(f"**GCS Bucket:** {self.prompt_manager.gcs_bucket_name}")
                st.info(f"**GCS Path:** {self.prompt_manager.gcs_dir_path}")

            # Local file stats
            st.subheader("File Statistics")
            local_stats = self.local_explorer.get_file_stats()
            st.metric("Local Files", local_stats["total_files"])
            st.metric("Local Size", f"{local_stats['total_size']:,} bytes")

            # GCS version count
            if st.session_state.gcs_configured and self.prompt_manager:
                try:
                    versions = self.prompt_manager.list_versions()
                    st.metric("GCS Versions", len(versions))
                except Exception:
                    st.metric("GCS Versions", "Error")

    def _render_search_and_filters(self) -> None:
        """Render search and filter controls."""
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_query = st.text_input(
                "🔍 Search Files",
                value=st.session_state.search_query,
                placeholder="Enter filename or path...",
            )
            st.session_state.search_query = search_query

        with col2:
            st.session_state.show_file_tree = st.checkbox(
                "🌳 Tree View", value=st.session_state.show_file_tree
            )

        with col3:
            st.session_state.comparison_mode = st.checkbox(
                "🔄 Compare Mode", value=st.session_state.comparison_mode
            )

    def _render_file_tree(self, files: List[tuple]) -> Optional[str]:
        """Render files in a tree-like structure."""
        if not files:
            st.info("No files found.")
            return None

        # Group files by directory
        file_tree = {}
        for display_name, full_path in files:
            parts = Path(display_name).parts
            current = file_tree

            # Build nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file
            filename = parts[-1]
            current[filename] = full_path

        # Render tree
        def render_tree_level(tree_dict: Dict, level: int = 0) -> Optional[str]:
            selected_file = None
            indent = "  " * level

            for name, value in sorted(tree_dict.items()):
                if isinstance(value, dict):
                    # Directory
                    st.markdown(f"{indent}📁 **{name}**")
                    sub_selected = render_tree_level(value, level + 1)
                    if sub_selected:
                        selected_file = sub_selected
                else:
                    # File
                    if st.button(f"{indent}📄 {name}", key=f"tree_{value}"):
                        selected_file = value

            return selected_file

        return render_tree_level(file_tree)

    def _render_file_browser(self) -> None:
        """Render the enhanced file browser."""
        st.subheader("📁 File Browser")

        # Version selector
        versions = ["local"]
        if st.session_state.gcs_configured and self.prompt_manager:
            try:
                gcs_versions = self.prompt_manager.list_versions()
                versions.extend(gcs_versions)
            except Exception as e:
                st.warning(f"Could not fetch GCS versions: {e}")

        selected_version = st.selectbox(
            "Select Version",
            versions,
            index=versions.index(st.session_state.selected_version)
            if st.session_state.selected_version in versions
            else 0,
        )
        st.session_state.selected_version = selected_version

        # Get files based on version and search
        if selected_version == "local":
            if st.session_state.search_query:
                files = self.local_explorer.search_files(st.session_state.search_query)
            else:
                # Get all local files
                local_dir = Path(self.prompt_manager.local_dir_path)
                files = []
                if local_dir.exists():
                    for file_path in local_dir.rglob("*.yaml"):
                        relative_path = file_path.relative_to(local_dir)
                        files.append((str(relative_path), str(file_path)))
                files = sorted(files)
        else:
            # GCS files
            if self.gcs_explorer:
                gcs_files = self.gcs_explorer.list_files_in_version(selected_version)
                files = [(f["name"], f["name"]) for f in gcs_files]

                # Apply search filter
                if st.session_state.search_query:
                    query_lower = st.session_state.search_query.lower()
                    files = [
                        (name, path)
                        for name, path in files
                        if query_lower in name.lower()
                    ]
            else:
                files = []

        # Render files
        if st.session_state.show_file_tree:
            selected_file = self._render_file_tree(files)
            if selected_file:
                st.session_state.selected_file = selected_file
        else:
            if files:
                file_options = [display_name for display_name, _ in files]
                selected_idx = 0

                # Try to maintain selection
                if st.session_state.selected_file:
                    for i, (_, path) in enumerate(files):
                        if path == st.session_state.selected_file:
                            selected_idx = i
                            break

                selected_file_display = st.selectbox(
                    "Select File", file_options, index=selected_idx
                )

                # Find full path
                for display_name, full_path in files:
                    if display_name == selected_file_display:
                        st.session_state.selected_file = full_path
                        break
            else:
                st.info("No files found.")
                st.session_state.selected_file = None

    def _load_file_content(self, file_path: str, version: str = "local") -> str:
        """Load file content with enhanced error handling."""
        if not self.prompt_manager:
            return "Error: Prompt manager not initialized"

        try:
            if version == "local":
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                # Load from GCS using the explorer
                if self.gcs_explorer:
                    content = self.gcs_explorer.get_file_content_from_gcs(
                        version, file_path
                    )
                    return (
                        content
                        if content is not None
                        else "Error: File not found in GCS"
                    )
                else:
                    return "Error: GCS not configured"
        except Exception as e:
            return f"Error loading file: {e}"

    def _render_file_content(self) -> None:
        """Render the file content viewer with enhanced features."""
        st.subheader("📄 File Content")

        if not st.session_state.selected_file:
            st.info("Select a file to view its content.")
            return

        # File metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**File:** {Path(st.session_state.selected_file).name}")
        with col2:
            st.info(f"**Version:** {st.session_state.selected_version}")
        with col3:
            if st.session_state.selected_version != "local":
                # Show GCS metadata
                if self.gcs_explorer:
                    files = self.gcs_explorer.list_files_in_version(
                        st.session_state.selected_version
                    )
                    file_info = next(
                        (
                            f
                            for f in files
                            if f["name"] == st.session_state.selected_file
                        ),
                        None,
                    )
                    if file_info and file_info["size"]:
                        st.info(f"**Size:** {file_info['size']:,} bytes")

        # Load content
        content = self._load_file_content(
            st.session_state.selected_file, st.session_state.selected_version
        )

        # Content tabs
        tab1, tab2 = st.tabs(["📝 Editor", "🔍 Preview"])

        with tab1:
            # YAML editor
            edited_content = st_ace(
                value=content,
                language="yaml",
                theme="monokai",
                key="yaml_editor",
                height=400,
                auto_update=False,
                wrap=True,
                font_size=14,
                show_gutter=True,
                show_print_margin=True,
            )

            # Save functionality for local files
            if (
                st.session_state.selected_version == "local"
                and edited_content != content
            ):
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("💾 Save Changes", type="primary"):
                        try:
                            with open(
                                st.session_state.selected_file, "w", encoding="utf-8"
                            ) as f:
                                f.write(edited_content)
                            st.success("File saved successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving file: {e}")
                with col2:
                    st.warning("⚠️ Unsaved changes detected")

        with tab2:
            # Structured preview
            try:
                yaml_data = yaml.safe_load(content)
                st.json(yaml_data)
            except yaml.YAMLError as e:
                st.error(f"Invalid YAML: {e}")
                st.code(content, language="yaml")

    def _render_version_comparison(self) -> None:
        """Render version comparison interface."""
        if not st.session_state.gcs_configured or not self.gcs_explorer:
            st.info("GCS configuration required for version comparison.")
            return

        st.subheader("🔄 Version Comparison")

        versions = ["local"] + self.prompt_manager.list_versions()

        col1, col2 = st.columns(2)
        with col1:
            version1 = st.selectbox("Version 1", versions, key="compare_v1")
        with col2:
            version2 = st.selectbox("Version 2", versions, key="compare_v2")

        if version1 != version2 and st.button("Compare Versions"):
            try:
                comparison = self.gcs_explorer.compare_versions(version1, version2)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"**Added ({len(comparison['added'])})**")
                    for file in comparison["added"]:
                        st.write(f"+ {file}")

                with col2:
                    st.error(f"**Removed ({len(comparison['removed'])})**")
                    for file in comparison["removed"]:
                        st.write(f"- {file}")

                with col3:
                    st.warning(f"**Modified ({len(comparison['modified'])})**")
                    for file in comparison["modified"]:
                        st.write(f"~ {file}")

            except Exception as e:
                st.error(f"Error comparing versions: {e}")

    def _render_version_management(self) -> None:
        """Render enhanced version management."""
        if not st.session_state.gcs_configured:
            st.info("Configure GCS settings to enable version management.")
            return

        st.subheader("🔄 Version Management")

        # Version overview
        try:
            versions = self.prompt_manager.list_versions()
            if versions:
                st.write(f"**Available Versions:** {len(versions)}")

                # Show version details in expandable sections
                for version in versions[:5]:  # Show latest 5 versions
                    with st.expander(f"Version {version}"):
                        if self.gcs_explorer:
                            metadata = self.gcs_explorer.get_version_metadata(version)
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Files", metadata["file_count"])
                            with col2:
                                st.metric("Size", f"{metadata['total_size']:,} bytes")
                            with col3:
                                if metadata["last_updated"]:
                                    updated_date = datetime.fromisoformat(
                                        metadata["last_updated"].replace("Z", "+00:00")
                                    )
                                    st.write(
                                        f"**Updated:** {updated_date.strftime('%Y-%m-%d %H:%M')}"
                                    )
        except Exception as e:
            st.error(f"Error loading version information: {e}")

        # Version actions
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Create New Version**")
            bump_type = st.selectbox(
                "Version Bump Type",
                ["major", "minor", "patch"],
                help="Type of version increment",
            )

            if st.button("📦 Save Snapshot", type="primary"):
                try:
                    with st.spinner("Creating snapshot..."):
                        # pyrefly: ignore
                        new_version = self.prompt_manager.save_snapshot(bump_type)
                    st.success(f"✅ Snapshot created: Version {new_version}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating snapshot: {e}")

        with col2:
            st.write("**Load Version**")
            versions = (
                self.prompt_manager.list_versions() if self.prompt_manager else []
            )
            if versions:
                version_to_load = st.selectbox(
                    "Select Version to Load",
                    versions,
                    help="Version to download and replace local files",
                )

                if st.button("⬇️ Load Version", type="secondary"):
                    if st.checkbox("⚠️ I understand this will replace local files"):
                        try:
                            with st.spinner("Loading version..."):
                                target_dir = self.prompt_manager.load_snapshot(
                                    version_to_load, replace=True
                                )
                            st.success(
                                f"✅ Version {version_to_load} loaded to {target_dir}"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error loading version: {e}")
            else:
                st.info("No GCS versions available.")

    def run(self) -> None:
        """Run the enhanced dashboard application."""
        st.set_page_config(
            page_title="Enhanced Prompt Manager Dashboard",
            page_icon="📝",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("📝 Prompt Manager Dashboard")
        st.markdown(
            "Comprehensive prompt management with local files and Google Cloud Storage integration."
        )

        if not self.prompt_manager:
            st.error("❌ No prompt manager provided to the dashboard.")
            return

        # Render sidebar stats
        self._render_sidebar_stats()

        # Search and filters
        self._render_search_and_filters()

        # Main content layout
        if st.session_state.comparison_mode:
            # Comparison mode
            self._render_version_comparison()
        else:
            # Normal mode
            col1, col2 = st.columns([1, 2])

            with col1:
                self._render_file_browser()

            with col2:
                self._render_file_content()

        # Version management
        st.divider()
        self._render_version_management()

        # Footer
        st.divider()
        st.markdown(
            """
            <div style='text-align: center; color: #666; padding: 20px;'>
                <small>Blob Prompt Manager Dashboard | Built with Streamlit</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main(prompt_manager: PromptManager | None = None):
    """Main entry point for the Streamlit app.

    Args:
        prompt_manager: Optional PromptManager instance. If not provided,
                       will show an error message.
    """
    if prompt_manager is None:
        st.error("❌ No PromptManager instance provided to the dashboard.")
        st.info("Please provide a PromptManager instance when calling main().")
        return

    dashboard = PromptDashboard(prompt_manager)
    dashboard.run()


if __name__ == "__main__":
    # Get the prompt manager instance from the runner module
    try:
        from blob_prompt_manager.dashboard.runner import get_prompt_manager

        prompt_manager = get_prompt_manager()
    except ImportError:
        prompt_manager = None

    main(prompt_manager)

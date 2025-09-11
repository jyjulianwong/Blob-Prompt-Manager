"""Utilities for enhanced GCS integration in the dashboard."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prompt2blob_vm.version_manager import VersionManager


class GCSFileExplorer:
    """Enhanced GCS file explorer for the dashboard."""

    def __init__(self, version_manager: VersionManager):
        """Initialize with a prompt manager instance."""
        self.version_manager = version_manager

    def list_files_in_version(self, version: str) -> List[Dict[str, str]]:
        """
        List all files in a specific GCS version with metadata.

        Args:
            version: Version string (e.g., "1.0.0")

        Returns:
            List of dictionaries containing file information
        """
        if not self.version_manager.gcs_bucket_name:
            return []

        try:
            gcs_client = self.version_manager._get_gcs_client()
            bucket = gcs_client.bucket(self.version_manager.gcs_bucket_name)

            version_prefix = f"{self.version_manager.gcs_dir_path}/Version {version}/"
            blobs = bucket.list_blobs(prefix=version_prefix)

            files = []
            for blob in blobs:
                if blob.name.endswith("/"):  # Skip directory markers
                    continue

                # Extract relative path within the version
                relative_path = blob.name[len(version_prefix) :]

                files.append(
                    # pyrefly: ignore
                    {
                        "name": relative_path,
                        "full_path": blob.name,
                        "size": blob.size,
                        "updated": blob.updated.isoformat() if blob.updated else None,
                        "content_type": blob.content_type,
                    }
                )

            return sorted(files, key=lambda x: x["name"])
        except Exception:
            return []

    def get_file_content_from_gcs(self, version: str, file_path: str) -> Optional[str]:
        """
        Get file content directly from GCS.

        Args:
            version: Version string
            file_path: Relative file path within the version

        Returns:
            File content as string or None if not found
        """
        if not self.version_manager.gcs_bucket_name:
            return None

        try:
            gcs_client = self.version_manager._get_gcs_client()
            bucket = gcs_client.bucket(self.version_manager.gcs_bucket_name)

            gcs_file_path = (
                f"{self.version_manager.gcs_dir_path}/Version {version}/{file_path}"
            )
            blob = bucket.blob(gcs_file_path)

            if blob.exists():
                return blob.download_as_text(encoding="utf-8")
            return None
        except Exception:
            return None

    def get_version_metadata(self, version: str) -> Dict[str, Any]:
        """
        Get metadata about a specific version.

        Args:
            version: Version string

        Returns:
            Dictionary containing version metadata
        """
        files = self.list_files_in_version(version)

        if not files:
            return {
                "file_count": 0,
                "total_size": 0,
                "last_updated": None,
                "file_types": [],
            }

        total_size = sum(f["size"] or 0 for f in files)
        last_updated = max((f["updated"] for f in files if f["updated"]), default=None)

        file_types = list(
            set(Path(f["name"]).suffix.lower() for f in files if Path(f["name"]).suffix)
        )

        return {
            "file_count": len(files),
            "total_size": total_size,
            "last_updated": last_updated,
            "file_types": file_types,
        }

    def compare_versions(self, version1: str, version2: str) -> Dict[str, List[str]]:
        """
        Compare files between two versions.

        Args:
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Dictionary with added, removed, and modified files
        """
        files1 = {f["name"]: f for f in self.list_files_in_version(version1)}
        files2 = {f["name"]: f for f in self.list_files_in_version(version2)}

        added = list(set(files2.keys()) - set(files1.keys()))
        removed = list(set(files1.keys()) - set(files2.keys()))

        # Check for modified files (size difference as a simple heuristic)
        modified = []
        for name in set(files1.keys()) & set(files2.keys()):
            if files1[name]["size"] != files2[name]["size"]:
                modified.append(name)

        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "modified": sorted(modified),
        }


class LocalFileExplorer:
    """Enhanced local file explorer for the dashboard."""

    def __init__(self, local_dir_path: str):
        """Initialize with local directory path."""
        self.local_dir = Path(local_dir_path)

    def get_file_tree(self) -> Dict[str, Any]:
        """
        Get a hierarchical representation of the local file structure.

        Returns:
            Nested dictionary representing the file tree
        """
        if not self.local_dir.exists():
            return {}

        def build_tree(path: Path) -> Dict[str, Any]:
            tree = {"type": "directory", "children": {}}

            try:
                for item in sorted(path.iterdir()):
                    if item.is_file() and item.suffix.lower() in [".yaml", ".yml"]:
                        # pyrefly: ignore
                        tree["children"][item.name] = {
                            "type": "file",
                            "path": str(item),
                            "size": item.stat().st_size,
                            "modified": item.stat().st_mtime,
                        }
                    elif item.is_dir() and not item.name.startswith("."):
                        subtree = build_tree(item)
                        if subtree["children"]:  # Only include non-empty directories
                            # pyrefly: ignore
                            tree["children"][item.name] = subtree
            except PermissionError:
                pass

            return tree

        return build_tree(self.local_dir)

    def search_files(self, query: str) -> List[Tuple[str, str]]:
        """
        Search for files matching a query.

        Args:
            query: Search query (matches file names and paths)

        Returns:
            List of tuples (display_name, full_path)
        """
        if not self.local_dir.exists():
            return []

        query_lower = query.lower()
        matches = []

        for file_path in self.local_dir.rglob("*.yaml"):
            relative_path = file_path.relative_to(self.local_dir)
            display_name = str(relative_path)

            if query_lower in display_name.lower():
                matches.append((display_name, str(file_path)))

        return sorted(matches)

    def get_file_stats(self) -> Dict[str, Any]:
        """
        Get statistics about local files.

        Returns:
            Dictionary containing file statistics
        """
        if not self.local_dir.exists():
            return {
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "directory_count": 0,
            }

        total_files = 0
        total_size = 0
        file_types = {}
        directories = set()

        for file_path in self.local_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                try:
                    size = file_path.stat().st_size
                    total_size += size

                    ext = file_path.suffix.lower()
                    if ext:
                        file_types[ext] = file_types.get(ext, 0) + 1
                except (OSError, PermissionError):
                    pass

                # Track directories
                directories.add(str(file_path.parent.relative_to(self.local_dir)))

        return {
            "total_files": total_files,
            "total_size": total_size,
            "file_types": file_types,
            "directory_count": len(directories),
        }

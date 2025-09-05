"""PromptManager class for managing prompts locally and in Google Cloud Storage."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from google.cloud import storage
from packaging import version


class PromptManager(ABC):
    """
    Abstract base class for managing prompts from local directory or Google Cloud Storage.

    This class provides functionality to load prompts either from a local 'prompts/' directory
    or from versioned folders in Google Cloud Storage. Users must implement the abstract
    get_prompt_file_path method to define how keys map to YAML file paths.
    """

    def __init__(
        self,
        local_dir_path: str = "prompts",
        gcs_bucket_name: Optional[str] = None,
        gcs_dir_path: Optional[str] = None,
        gcs_credentials_path: Optional[str] = None,
    ):
        """
        Initialize the PromptManager.

        Args:
            gcs_bucket_name: Google Cloud Storage bucket name for versioned prompts
            gcs_dir_path: Path within the GCS bucket to store versioned prompt folders
            local_dir_path: Local directory containing prompts (default: "prompts")
            gcs_credentials_path: Path to GCS credentials JSON file (optional)
        """
        self.local_dir_path = Path(local_dir_path)
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_dir_path = gcs_dir_path.rstrip("/") if gcs_dir_path else None

        # Initialize GCS client if bucket is provided
        self._gcs_client = None
        if gcs_bucket_name:
            if gcs_credentials_path:
                self._gcs_client = storage.Client.from_service_account_json(
                    gcs_credentials_path
                )
            else:
                self._gcs_client = storage.Client()

    def _get_gcs_client(self) -> storage.Client:
        """Get GCS client."""
        if (
            self._gcs_client is None
            or not self.gcs_bucket_name
            or not self.gcs_dir_path
        ):
            raise ValueError("GCS configuration required for this operation")

        return self._gcs_client

    def _load_local_prompt(self, keys: List[str]) -> Dict[str, Any]:
        """Load prompt from local directory."""
        file_path = self.get_prompt_file_path(keys)
        full_path = self.local_dir_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_gcs_prompt(self, keys: List[str], version: str) -> Dict[str, Any]:
        """Load prompt from GCS versioned folder."""
        gcs_client = self._get_gcs_client()

        file_path = self.get_prompt_file_path(keys)
        gcs_file_path = f"{self.gcs_dir_path}/Version {version}/{file_path}"

        bucket = gcs_client.bucket(self.gcs_bucket_name)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            raise FileNotFoundError(f"Prompt file not found in GCS: {gcs_file_path}")

        content = blob.download_as_text(encoding="utf-8")
        return yaml.safe_load(content)

    def _get_next_version(self, bump_type: Literal["major", "minor", "patch"]) -> str:
        """Calculate the next version number based on existing versions in GCS."""
        gcs_client = self._get_gcs_client()

        bucket = gcs_client.bucket(self.gcs_bucket_name)

        # List all version folders by parsing from actual file paths
        prefix = f"{self.gcs_dir_path}/Version " if self.gcs_dir_path else "Version "
        blobs = bucket.list_blobs(prefix=prefix)

        existing_versions = set()  # Use set to avoid duplicates
        for blob in blobs:
            # Extract version from blob path like "tmp/prompt-artifacts/Version 1.0.0/file.yaml"
            blob_path = blob.name
            if blob_path.startswith(prefix):
                # Find the version part after "Version "
                remaining_path = blob_path[len(prefix) :]
                # Get the version directory (first part before next slash)
                version_part = remaining_path.split("/")[0]
                try:
                    existing_versions.add(version.parse(version_part))
                except version.InvalidVersion:
                    continue

        if not existing_versions:
            # No existing versions, start with 1.0.0
            if bump_type == "major":
                return "1.0.0"
            elif bump_type == "minor":
                return "0.1.0"
            else:  # patch
                return "0.0.1"

        # Get the latest version
        latest_version = max(existing_versions)

        # Calculate next version based on bump type
        if bump_type == "major":
            next_version = version.Version(f"{latest_version.major + 1}.0.0")
        elif bump_type == "minor":
            next_version = version.Version(
                f"{latest_version.major}.{latest_version.minor + 1}.0"
            )
        else:  # patch
            next_version = version.Version(
                f"{latest_version.major}.{latest_version.minor}.{latest_version.micro + 1}"
            )

        return str(next_version)

    def _upload_dir_to_gcs(self, version: str) -> None:
        """Upload the entire local prompts directory to GCS under a version folder."""
        gcs_client = self._get_gcs_client()

        bucket = gcs_client.bucket(self.gcs_bucket_name)

        for file_path in self.local_dir_path.rglob("*"):
            if file_path.is_file():
                # Calculate relative path from prompts directory
                relative_path = file_path.relative_to(self.local_dir_path)

                # Create GCS blob path
                gcs_blob_path = f"{self.gcs_dir_path}/Version {version}/{relative_path}"

                # Upload file
                blob = bucket.blob(gcs_blob_path)
                blob.upload_from_filename(str(file_path))

    def _download_gcs_to_dir(self, version: str, target_dir: Path) -> None:
        """Download a specific version folder from GCS to a local directory."""
        gcs_client = self._get_gcs_client()

        bucket = gcs_client.bucket(self.gcs_bucket_name)
        version_prefix = f"{self.gcs_dir_path}/Version {version}/"

        # List all blobs with the version prefix
        blobs = bucket.list_blobs(prefix=version_prefix)

        for blob in blobs:
            # Skip if it's just a directory marker
            if blob.name.endswith("/"):
                continue

            # Calculate the relative path within the version folder
            relative_path = blob.name[len(version_prefix) :]

            # Create the target file path
            target_file_path = target_dir / relative_path

            # Create parent directories if they don't exist
            target_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Download the file
            blob.download_to_filename(str(target_file_path))

    @abstractmethod
    def get_prompt_file_path(self, keys: List[str]) -> str:
        """
        Abstract method to get the file path for a prompt given a list of keys.

        Args:
            keys: List of keys identifying the prompt

        Returns:
            File path relative to the prompts/ folder (e.g., "customized/brand_1/metric_1.yaml")
        """
        raise NotImplementedError(
            "get_prompt_file_path must be implemented by subclasses"
        )

    def list_versions(self) -> List[str]:
        """
        List all available versions in GCS.

        Returns:
            List of version numbers sorted in descending order

        Raises:
            ValueError: If GCS is not configured
        """
        gcs_client = self._get_gcs_client()

        bucket = gcs_client.bucket(self.gcs_bucket_name)
        prefix = f"{self.gcs_dir_path}/Version " if self.gcs_dir_path else "Version "

        versions = set()  # Use set to avoid duplicates
        for blob in bucket.list_blobs(prefix=prefix):
            # Extract version from blob path like "tmp/prompt-artifacts/Version 1.0.0/file.yaml"
            blob_path = blob.name
            if blob_path.startswith(prefix):
                # Find the version part after "Version "
                remaining_path = blob_path[len(prefix) :]
                # Get the version directory (first part before next slash)
                version_part = remaining_path.split("/")[0]
                try:
                    version.parse(version_part)  # Validate version format
                    versions.add(version_part)
                except version.InvalidVersion:
                    continue

        # Convert to list and sort versions in descending order
        versions_list = list(versions)
        versions_list.sort(key=lambda v: version.parse(v), reverse=True)
        return versions_list

    def load_prompt(self, keys: List[str], version: str = "local") -> Dict[str, Any]:
        """
        Load a prompt from either local directory or a specific version in GCS.

        Args:
            keys: List of keys identifying the prompt
            version: Version to load ("local" for local directory, "latest" for most recent GCS version, or specific version number like "1.0")

        Returns:
            Dictionary containing the parsed YAML content

        Raises:
            FileNotFoundError: If the prompt file is not found
            ValueError: If version is not "local" but GCS is not configured, or if no versions exist when using "latest"
        """
        if version == "local":
            return self._load_local_prompt(keys)
        elif version == "latest":
            # Get the latest version from GCS
            versions = self.list_versions()
            if not versions:
                raise ValueError("No versions found in GCS")
            latest_version = versions[
                0
            ]  # list_versions returns sorted in descending order
            return self._load_gcs_prompt(keys, latest_version)
        else:
            return self._load_gcs_prompt(keys, version)

    def load_prompt_as_str(
        self, keys: List[str], version: str = "local", field: Optional[str] = None
    ) -> str:
        """
        Get a prompt as a string, optionally extracting a specific field.

        Args:
            keys: List of keys identifying the prompt
            version: Version to load ("local" for local directory, "latest" for most recent GCS version, or specific version number)
            field: Optional field to extract from the YAML (e.g., "extraction_instructions")

        Returns:
            String representation of the prompt or specific field
        """
        prompt_data = self.load_prompt(keys, version)

        if field:
            if field not in prompt_data:
                raise KeyError(f"Field '{field}' not found in prompt")
            return str(prompt_data[field])

        # Return the entire prompt as a formatted string
        return yaml.dump(prompt_data, default_flow_style=False, allow_unicode=True)

    def save_snapshot(
        self, next_version_bump: Literal["major", "minor", "patch"] = "major"
    ) -> str:
        """
        Save a snapshot of local prompts to GCS with version bumping.

        Args:
            next_version_bump: Type of version bump ("major", "minor", or "patch")

        Returns:
            The new version number that was created

        Raises:
            ValueError: If GCS is not configured
        """
        # Get the next version number
        next_version = self._get_next_version(next_version_bump)

        # Upload all files from local prompts directory
        self._upload_dir_to_gcs(next_version)

        return next_version

    def load_snapshot(
        self, version: str, target_dir: Optional[str] = None, replace: bool = False
    ) -> str:
        """
        Download a specific version from GCS and save it to a local directory.

        Args:
            version: Version to download (e.g., "1.0.0" or "latest")
            target_dir: Target directory to save the snapshot. If None and replace=True,
                       uses the configured local_dir_path
            replace: If True, replaces the existing local prompts directory. If False,
                    target_dir must be provided

        Returns:
            Path to the directory where the snapshot was saved

        Raises:
            ValueError: If GCS is not configured, if replace=False and target_dir is None,
                       or if version is "latest" but no versions exist
            FileNotFoundError: If the specified version doesn't exist in GCS
        """
        gcs_client = self._get_gcs_client()

        if not replace and target_dir is None:
            raise ValueError("target_dir must be provided when replace=False")

        # Handle "latest" version
        if version == "latest":
            versions = self.list_versions()
            if not versions:
                raise ValueError("No versions found in GCS")
            version = versions[0]  # list_versions returns sorted in descending order

        # Validate that the version exists
        bucket = gcs_client.bucket(self.gcs_bucket_name)
        version_prefix = f"{self.gcs_dir_path}/Version {version}/"

        # Check if any blobs exist with this version prefix
        blobs = list(bucket.list_blobs(prefix=version_prefix, max_results=1))
        if not blobs:
            raise FileNotFoundError(f"Version {version} not found in GCS")

        # Determine target directory
        if replace:
            # Use configured local directory and replace it
            final_target_dir = self.local_dir_path
            if final_target_dir.exists():
                shutil.rmtree(final_target_dir)
        else:
            # Use provided target directory
            final_target_dir = Path(target_dir)  # pyrefly: ignore
            if final_target_dir.exists():
                raise FileExistsError(
                    f"Target directory already exists: {final_target_dir}"
                )

        # Create the target directory
        final_target_dir.mkdir(parents=True, exist_ok=True)

        # Download the version folder
        self._download_gcs_to_dir(version, final_target_dir)

        return str(final_target_dir)

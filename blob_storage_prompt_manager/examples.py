"""Example implementations of PromptManager for different use cases."""

from typing import List

from blob_storage_prompt_manager.prompt_manager import PromptManager


class BrandMetricPromptManager(PromptManager):
    """
    Example implementation for brand-specific metric prompts.

    This implementation maps keys like ["Goldman Sachs", "TVPI"] to file paths
    like "customized/goldman_sachs/tvpi.yaml" or falls back to generic prompts.
    """

    def get_prompt_file_path(self, keys: List[str]) -> str:
        """
        Map keys to file paths for brand-specific metric prompts.

        Args:
            keys: List of keys [brand_name, metric_name]

        Returns:
            File path relative to prompts/ directory

        Example:
            ["Goldman Sachs", "TVPI"] -> "customized/goldman_sachs/tvpi.yaml"
            ["Generic", "TVPI"] -> "generic/tvpi.yaml"
        """
        if len(keys) != 2:
            raise ValueError("Expected exactly 2 keys: [brand_name, metric_name]")

        brand_name, metric_name = keys

        # Normalize names for file paths
        brand_slug = self._normalize_name(brand_name)
        metric_slug = self._normalize_name(metric_name)

        # Check if this is a generic prompt request
        if brand_name.lower() == "generic":
            return f"generic/{metric_slug}.yaml"

        # Return customized brand-specific path
        return f"customized/{brand_slug}/{metric_slug}.yaml"

    def _normalize_name(self, name: str) -> str:
        """Convert a name to a file-system friendly slug."""
        return name.lower().replace(" ", "_").replace("-", "_")


class HierarchicalPromptManager(PromptManager):
    """
    Example implementation for hierarchical prompt organization.

    This implementation supports variable-length keys for nested directory structures.
    """

    def get_prompt_file_path(self, keys: List[str]) -> str:
        """
        Map keys to hierarchical file paths.

        Args:
            keys: List of keys representing the hierarchy

        Returns:
            File path relative to prompts/ directory

        Example:
            ["finance", "metrics", "tvpi"] -> "finance/metrics/tvpi.yaml"
            ["marketing", "campaigns"] -> "marketing/campaigns.yaml"
        """
        if not keys:
            raise ValueError("At least one key is required")

        # Normalize all keys for file paths
        normalized_keys = [self._normalize_name(key) for key in keys]

        # Last key becomes the filename, others become directory structure
        if len(normalized_keys) == 1:
            return f"{normalized_keys[0]}.yaml"
        else:
            directories = "/".join(normalized_keys[:-1])
            filename = normalized_keys[-1]
            return f"{directories}/{filename}.yaml"

    def _normalize_name(self, name: str) -> str:
        """Convert a name to a file-system friendly slug."""
        return name.lower().replace(" ", "_").replace("-", "_")


# Example usage functions
def example_brand_metric_usage():
    """Example of how to use the BrandMetricPromptManager."""
    # Initialize with GCS configuration
    manager = BrandMetricPromptManager(
        local_dir_path="prompts",
        gcs_bucket_name="my-prompts-bucket",
        gcs_dir_path="prompt-artifacts",
    )

    # Load a prompt from local directory
    try:
        local_prompt = manager.load_prompt(
            keys=["Goldman Sachs", "TVPI"], version="local"
        )
        print("Local prompt loaded:", local_prompt)
    except FileNotFoundError:
        print("Local prompt not found")

    # Load a prompt from a specific version in GCS
    try:
        versioned_prompt = manager.load_prompt(
            keys=["Goldman Sachs", "TVPI"], version="1.0"
        )
        print("Versioned prompt loaded:", versioned_prompt)
    except FileNotFoundError:
        print("Versioned prompt not found")

    # Save a snapshot with major version bump
    try:
        new_version = manager.save_snapshot(next_version_bump="major")
        print(f"Snapshot saved as version: {new_version}")
    except Exception as e:
        print(f"Error saving snapshot: {e}")

    # List all available versions
    try:
        versions = manager.list_versions()
        print("Available versions:", versions)
    except Exception as e:
        print(f"Error listing versions: {e}")


def example_hierarchical_usage():
    """Example of how to use the HierarchicalPromptManager."""
    manager = HierarchicalPromptManager(
        gcs_bucket_name="my-prompts-bucket", gcs_dir_path="hierarchical-prompts"
    )

    # Load prompts with different hierarchical structures
    try:
        finance_prompt = manager.load_prompt(
            keys=["finance", "metrics", "tvpi"], version="local"
        )
        print("Finance prompt:", finance_prompt)
    except FileNotFoundError:
        print("Finance prompt not found")

    try:
        marketing_prompt = manager.load_prompt(
            keys=["marketing", "campaigns"], version="local"
        )
        print("Marketing prompt:", marketing_prompt)
    except FileNotFoundError:
        print("Marketing prompt not found")


if __name__ == "__main__":
    print("\n=== Brand Metric Example ===")
    example_brand_metric_usage()

    print("\n=== Hierarchical Example ===")
    example_hierarchical_usage()

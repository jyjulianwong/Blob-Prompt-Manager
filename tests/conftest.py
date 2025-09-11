"""Pytest configuration and fixtures for VersionManager tests."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from prompt2blob_vm.version_manager import VersionManager


class ConcreteVersionManager(VersionManager):
    """Concrete implementation of VersionManager for testing."""

    def get_prompt_file_path(self, keys: list[str]) -> str:
        """
        Simple implementation that joins keys with slashes and adds .yaml extension.

        Args:
            keys: List of keys (e.g., ["customized", "brand_1", "metric_1"])

        Returns:
            File path like "customized/brand_1/metric_1.yaml"
        """
        return "/".join(keys) + ".yaml"


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary directory with sample prompt files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()

        # Create sample YAML files
        sample_prompts = {
            "generic/metric_1.yaml": {
                "metric_1": {
                    "description": "This is a generic prompt.",
                    "synonyms": ["Metric 1", "metric 1", "metric-1"],
                    "extraction_instructions": "Extract the following information from the text: [information]",
                }
            },
            "customized/brand_1/metric_1.yaml": {
                "metric_1": {
                    "description": "This is a brand 1 specific prompt.",
                    "synonyms": ["Brand 1 Metric", "b1-metric"],
                    "extraction_instructions": "Extract brand 1 specific information: [info]",
                }
            },
            "customized/brand_2/metric_1.yaml": {
                "metric_1": {
                    "description": "This is a brand 2 specific prompt.",
                    "synonyms": ["Brand 2 Metric", "b2-metric"],
                    "extraction_instructions": "Extract brand 2 specific information: [info]",
                }
            },
        }

        for file_path, content in sample_prompts.items():
            full_path = prompts_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

        yield str(prompts_dir)


@pytest.fixture
def mock_gcs_client():
    """Create a mock GCS client with common methods."""
    client = Mock()
    bucket = Mock()
    client.bucket.return_value = bucket

    # Mock blob operations
    blob = Mock()
    bucket.blob.return_value = blob
    bucket.list_blobs.return_value = []

    blob.exists.return_value = True
    blob.download_as_text.return_value = yaml.dump(
        {
            "test_metric": {
                "description": "Test prompt from GCS",
                "extraction_instructions": "Test instructions",
            }
        }
    )

    return client


@pytest.fixture
def version_manager_local(temp_prompts_dir):
    """Create a VersionManager instance configured for local-only operations."""
    return ConcreteVersionManager(local_dir_path=temp_prompts_dir)


@pytest.fixture
def version_manager_gcs(temp_prompts_dir, mock_gcs_client):
    """Create a VersionManager instance configured with mocked GCS."""
    manager = ConcreteVersionManager(
        local_dir_path=temp_prompts_dir,
        gcs_bucket_name="test-bucket",
        gcs_dir_path="test-prompts",
    )
    manager._gcs_client = mock_gcs_client
    return manager


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content for testing."""
    return {
        "test_metric": {
            "description": "Sample test prompt",
            "synonyms": ["test", "sample"],
            "extraction_instructions": "Extract test information",
        }
    }

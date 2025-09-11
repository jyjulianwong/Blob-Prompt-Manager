"""Unit tests for VersionManager class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from prompt2blob_vm.version_manager import VersionManager

from .conftest import ConcreteVersionManager


class TestVersionManagerInit:
    """Test VersionManager initialization."""

    def test_init_local_only(self):
        """Test initialization with local directory only."""
        manager = ConcreteVersionManager(local_dir_path="test_prompts")

        assert str(manager.local_dir_path) == "test_prompts"
        assert manager.gcs_bucket_name is None
        assert manager.gcs_dir_path is None
        assert manager._gcs_client is None

    def test_init_with_gcs_config(self):
        """Test initialization with GCS configuration."""
        with patch("prompt2blob_vm.version_manager.storage.Client") as mock_client:
            manager = ConcreteVersionManager(
                local_dir_path="test_prompts",
                gcs_bucket_name="test-bucket",
                gcs_dir_path="prompts/",
                gcs_credentials_path="credentials.json",
            )

            assert str(manager.local_dir_path) == "test_prompts"
            assert manager.gcs_bucket_name == "test-bucket"
            assert manager.gcs_dir_path == "prompts"  # Should strip trailing slash
            mock_client.from_service_account_json.assert_called_once_with(
                "credentials.json"
            )

    def test_init_with_gcs_no_credentials(self):
        """Test initialization with GCS but no credentials file."""
        with patch("prompt2blob_vm.version_manager.storage.Client") as mock_client:
            manager = ConcreteVersionManager(
                gcs_bucket_name="test-bucket", gcs_dir_path="prompts"
            )

            mock_client.assert_called_once()
            assert manager._gcs_client is not None

    def test_init_with_ignore_files(self):
        """Test initialization with ignore_files parameter."""
        ignore_patterns = ["*.log", "*.tmp", "cache/*"]
        manager = ConcreteVersionManager(
            local_dir_path="test_prompts", ignore_files=ignore_patterns
        )

        assert manager.ignore_files == ignore_patterns

    def test_init_with_ignore_files_none(self):
        """Test initialization with ignore_files=None."""
        manager = ConcreteVersionManager(local_dir_path="test_prompts")

        assert manager.ignore_files == []


class TestLocalPromptOperations:
    """Test local prompt loading operations."""

    def test_load_local_prompt_success(self, version_manager_local):
        """Test successful loading of local prompt."""
        result = version_manager_local.load_prompt(["generic", "metric_1"])

        assert "metric_1" in result
        assert result["metric_1"]["description"] == "This is a generic prompt."
        assert "synonyms" in result["metric_1"]
        assert "extraction_instructions" in result["metric_1"]

    def test_load_local_prompt_customized(self, version_manager_local):
        """Test loading customized prompt."""
        result = version_manager_local.load_prompt(
            ["customized", "brand_1", "metric_1"]
        )

        assert "metric_1" in result
        assert result["metric_1"]["description"] == "This is a brand 1 specific prompt."
        assert "Brand 1 Metric" in result["metric_1"]["synonyms"]

    def test_load_local_prompt_not_found(self, version_manager_local):
        """Test loading non-existent local prompt."""
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            version_manager_local.load_prompt(["nonexistent", "prompt"])

    def test_load_prompt_as_str_full(self, version_manager_local):
        """Test loading prompt as full YAML string."""
        result = version_manager_local.load_prompt_as_str(["generic", "metric_1"])

        assert isinstance(result, str)
        assert "metric_1:" in result
        assert "description: This is a generic prompt." in result

    def test_load_prompt_as_str_specific_field(self, version_manager_local):
        """Test loading specific field from prompt."""
        result = version_manager_local.load_prompt_as_str(
            ["generic", "metric_1"], field="metric_1"
        )

        # Should return the metric_1 section as a string representation
        assert "'description': 'This is a generic prompt.'" in result
        assert "'synonyms'" in result

    def test_load_prompt_as_str_field_not_found(self, version_manager_local):
        """Test loading non-existent field from prompt."""
        with pytest.raises(KeyError, match="Field 'nonexistent' not found"):
            version_manager_local.load_prompt_as_str(
                ["generic", "metric_1"], field="nonexistent"
            )


class TestGCSPromptOperations:
    """Test GCS prompt operations with mocking."""

    def test_load_gcs_prompt_success(self, version_manager_gcs, sample_yaml_content):
        """Test successful loading of GCS prompt."""
        # Setup mock
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.exists.return_value = True
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.download_as_text.return_value = yaml.dump(
            sample_yaml_content
        )

        result = version_manager_gcs.load_prompt(["test", "prompt"], version="1.0.0")

        assert "test_metric" in result
        assert result["test_metric"]["description"] == "Sample test prompt"

    def test_load_gcs_prompt_not_found(self, version_manager_gcs):
        """Test loading non-existent GCS prompt."""
        # Setup mock to return False for exists()
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Prompt file not found in GCS"):
            version_manager_gcs.load_prompt(["test", "prompt"], version="1.0.0")

    def test_load_gcs_prompt_no_config(self, version_manager_local):
        """Test loading GCS prompt without GCS configuration."""
        with pytest.raises(ValueError, match="GCS configuration required"):
            version_manager_local.load_prompt(["test", "prompt"], version="1.0.0")

    def test_load_prompt_latest_version(self, version_manager_gcs, sample_yaml_content):
        """Test loading latest version from GCS."""
        # Mock list_versions to return sorted versions
        mock_blobs = [
            Mock(name="test-prompts/Version 1.0.0/test.yaml"),
            Mock(name="test-prompts/Version 1.1.0/test.yaml"),
            Mock(name="test-prompts/Version 2.0.0/test.yaml"),
        ]
        for i, blob in enumerate(mock_blobs):
            blob.name = (
                f"test-prompts/Version {['1.0.0', '1.1.0', '2.0.0'][i]}/test.yaml"
            )

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.exists.return_value = True
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.download_as_text.return_value = yaml.dump(
            sample_yaml_content
        )

        result = version_manager_gcs.load_prompt(["test", "prompt"], version="latest")

        assert "test_metric" in result
        # Verify it called with the latest version (2.0.0)
        version_manager_gcs._gcs_client.bucket.return_value.blob.assert_called_with(
            "test-prompts/Version 2.0.0/test/prompt.yaml"
        )

    def test_load_prompt_latest_no_versions(self, version_manager_gcs):
        """Test loading latest version when no versions exist."""
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = []

        with pytest.raises(ValueError, match="No versions found in GCS"):
            version_manager_gcs.load_prompt(["test", "prompt"], version="latest")


class TestVersionManagement:
    """Test version management functionality."""

    def test_list_versions_success(self, version_manager_gcs):
        """Test successful listing of versions."""
        mock_blobs = [
            Mock(name="test-prompts/Version 1.0.0/test.yaml"),
            Mock(name="test-prompts/Version 1.1.0/test.yaml"),
            Mock(name="test-prompts/Version 2.0.0/test.yaml"),
            Mock(name="test-prompts/Version 0.9.0/test.yaml"),
        ]
        for i, blob in enumerate(mock_blobs):
            blob.name = f"test-prompts/Version {['1.0.0', '1.1.0', '2.0.0', '0.9.0'][i]}/test.yaml"

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        versions = version_manager_gcs.list_versions()

        # Should be sorted in descending order
        assert versions == ["2.0.0", "1.1.0", "1.0.0", "0.9.0"]

    def test_list_versions_no_gcs_config(self, version_manager_local):
        """Test listing versions without GCS configuration."""
        with pytest.raises(ValueError, match="GCS configuration required"):
            version_manager_local.list_versions()

    def test_list_versions_with_invalid_versions(self, version_manager_gcs):
        """Test listing versions with some invalid version strings."""
        mock_blobs = [
            Mock(name="test-prompts/Version 1.0.0/test.yaml"),
            Mock(name="test-prompts/Version invalid/test.yaml"),
            Mock(name="test-prompts/Version 2.0.0/test.yaml"),
        ]
        for i, blob in enumerate(mock_blobs):
            blob.name = (
                f"test-prompts/Version {['1.0.0', 'invalid', '2.0.0'][i]}/test.yaml"
            )

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        versions = version_manager_gcs.list_versions()

        # Should only include valid versions
        assert versions == ["2.0.0", "1.0.0"]

    def test_get_next_version_no_existing(self, version_manager_gcs):
        """Test getting next version when no versions exist."""
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = []

        # Test different bump types for first version
        assert version_manager_gcs._get_next_version("major") == "1.0.0"
        assert version_manager_gcs._get_next_version("minor") == "0.1.0"
        assert version_manager_gcs._get_next_version("patch") == "0.0.1"

    def test_get_next_version_with_existing(self, version_manager_gcs):
        """Test getting next version with existing versions."""
        mock_blobs = [
            Mock(name="test-prompts/Version 1.2.3/test.yaml"),
        ]
        mock_blobs[0].name = "test-prompts/Version 1.2.3/test.yaml"

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        assert version_manager_gcs._get_next_version("major") == "2.0.0"
        assert version_manager_gcs._get_next_version("minor") == "1.3.0"
        assert version_manager_gcs._get_next_version("patch") == "1.2.4"


class TestSnapshotOperations:
    """Test snapshot save and load operations."""

    def test_save_snapshot_success(self, version_manager_gcs):
        """Test successful snapshot saving."""
        # Mock existing versions
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = []

        # Mock the _upload_dir_to_gcs method instead of patching Path methods
        with patch.object(version_manager_gcs, "_upload_dir_to_gcs") as mock_upload:
            version = version_manager_gcs.save_snapshot("major")

            assert version == "1.0.0"
            mock_upload.assert_called_once_with("1.0.0")

    def test_save_snapshot_no_gcs_config(self, version_manager_local):
        """Test saving snapshot without GCS configuration."""
        with pytest.raises(ValueError, match="GCS configuration required"):
            version_manager_local.save_snapshot()

    def test_load_snapshot_success(self, version_manager_gcs):
        """Test successful snapshot loading."""
        # Mock version existence check
        mock_blobs = [Mock(name="test-prompts/Version 1.0.0/test.yaml")]
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "downloaded_prompts"

            # Mock the download process
            with patch.object(
                version_manager_gcs, "_download_gcs_to_dir"
            ) as mock_download:
                result_path = version_manager_gcs.load_snapshot(
                    "1.0.0", str(target_dir)
                )

                assert result_path == str(target_dir)
                mock_download.assert_called_once_with("1.0.0", target_dir)

    def test_load_snapshot_replace_local(self, version_manager_gcs):
        """Test loading snapshot with replace=True."""
        # Mock version existence check
        mock_blobs = [Mock(name="test-prompts/Version 1.0.0/test.yaml")]
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        with (
            patch.object(version_manager_gcs, "_download_gcs_to_dir") as mock_download,
            patch("shutil.rmtree") as mock_rmtree,
            patch("pathlib.Path.exists", return_value=True),
        ):
            result_path = version_manager_gcs.load_snapshot("1.0.0", replace=True)

            assert result_path == str(version_manager_gcs.local_dir_path)
            mock_rmtree.assert_called_once_with(version_manager_gcs.local_dir_path)
            mock_download.assert_called_once()

    def test_load_snapshot_latest_version(self, version_manager_gcs):
        """Test loading latest snapshot."""
        # Mock version listing
        mock_blobs_list = [
            Mock(name="test-prompts/Version 1.0.0/test.yaml"),
            Mock(name="test-prompts/Version 2.0.0/test.yaml"),
        ]
        mock_blobs_check = [Mock(name="test-prompts/Version 2.0.0/test.yaml")]

        # Configure mock blobs with proper name attributes
        for i, version_str in enumerate(["1.0.0", "2.0.0"]):
            mock_blobs_list[i].name = f"test-prompts/Version {version_str}/test.yaml"
        mock_blobs_check[0].name = "test-prompts/Version 2.0.0/test.yaml"

        # Mock list_blobs to return different results for listing vs checking
        def mock_list_blobs(prefix=None, **kwargs):
            if "max_results" in kwargs:
                return mock_blobs_check  # For existence check
            return mock_blobs_list  # For version listing

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.side_effect = (
            mock_list_blobs
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "downloaded_prompts"

            with patch.object(
                version_manager_gcs, "_download_gcs_to_dir"
            ) as mock_download:
                result_path = version_manager_gcs.load_snapshot(
                    "latest", str(target_dir)
                )

                assert result_path == str(target_dir)
                mock_download.assert_called_once_with("2.0.0", target_dir)

    def test_load_snapshot_version_not_found(self, version_manager_gcs):
        """Test loading non-existent snapshot version."""
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = []

        with pytest.raises(FileNotFoundError, match="Version 1.0.0 not found in GCS"):
            version_manager_gcs.load_snapshot("1.0.0", "target_dir")

    def test_load_snapshot_no_gcs_config(self, version_manager_local):
        """Test loading snapshot without GCS configuration."""
        with pytest.raises(ValueError, match="GCS configuration required"):
            version_manager_local.load_snapshot("1.0.0", "target_dir")

    def test_load_snapshot_invalid_params(self, version_manager_gcs):
        """Test loading snapshot with invalid parameters."""
        with pytest.raises(
            ValueError, match="target_dir must be provided when replace=False"
        ):
            version_manager_gcs.load_snapshot("1.0.0", replace=False)

    def test_load_snapshot_target_exists(self, version_manager_gcs):
        """Test loading snapshot when target directory already exists."""
        mock_blobs = [Mock(name="test-prompts/Version 1.0.0/test.yaml")]
        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()

            with pytest.raises(
                FileExistsError, match="Target directory already exists"
            ):
                version_manager_gcs.load_snapshot("1.0.0", str(existing_dir))


class TestIgnoreFunctionality:
    """Test ignore files functionality."""

    def test_should_ignore_file_no_patterns(self):
        """Test _should_ignore_file with no ignore patterns."""
        manager = ConcreteVersionManager(local_dir_path="test_prompts")
        test_file = Path("test_prompts/some_file.yaml")

        assert not manager._should_ignore_file(test_file)

    def test_should_ignore_file_with_patterns(self):
        """Test _should_ignore_file with various patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            prompts_dir.mkdir()

            manager = ConcreteVersionManager(
                local_dir_path=str(prompts_dir),
                ignore_files=["*.log", "*.tmp", "cache/*", "temp_*"],
            )

            # Test files that should be ignored
            log_file = prompts_dir / "debug.log"
            tmp_file = prompts_dir / "temporary.tmp"
            cache_file = prompts_dir / "cache" / "data.yaml"
            temp_file = prompts_dir / "temp_backup.yaml"

            assert manager._should_ignore_file(log_file)
            assert manager._should_ignore_file(tmp_file)
            assert manager._should_ignore_file(cache_file)
            assert manager._should_ignore_file(temp_file)

            # Test files that should not be ignored
            yaml_file = prompts_dir / "prompt.yaml"
            json_file = prompts_dir / "config.json"

            assert not manager._should_ignore_file(yaml_file)
            assert not manager._should_ignore_file(json_file)

    def test_should_ignore_file_subdirectories(self):
        """Test _should_ignore_file with files in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            prompts_dir.mkdir()

            manager = ConcreteVersionManager(
                local_dir_path=str(prompts_dir), ignore_files=["*.log", "subdir/*.tmp"]
            )

            # Test files in subdirectories
            subdir_log = prompts_dir / "custom" / "brand1" / "debug.log"
            subdir_tmp = prompts_dir / "subdir" / "temp.tmp"
            subdir_yaml = prompts_dir / "subdir" / "prompt.yaml"

            assert manager._should_ignore_file(subdir_log)  # *.log matches anywhere
            assert manager._should_ignore_file(subdir_tmp)  # subdir/*.tmp matches
            assert not manager._should_ignore_file(subdir_yaml)  # Not matching pattern

    def test_should_ignore_gcs_path_no_patterns(self):
        """Test _should_ignore_gcs_path with no ignore patterns."""
        manager = ConcreteVersionManager(local_dir_path="test_prompts")

        assert not manager._should_ignore_gcs_path("some/file.yaml")

    def test_should_ignore_gcs_path_with_patterns(self):
        """Test _should_ignore_gcs_path with various patterns."""
        manager = ConcreteVersionManager(
            local_dir_path="test_prompts",
            ignore_files=["*.log", "*.tmp", "cache/*", "temp_*"],
        )

        # Test paths that should be ignored
        assert manager._should_ignore_gcs_path("debug.log")
        assert manager._should_ignore_gcs_path("temporary.tmp")
        assert manager._should_ignore_gcs_path("cache/data.yaml")
        assert manager._should_ignore_gcs_path("temp_backup.yaml")
        assert manager._should_ignore_gcs_path("subdir/debug.log")

        # Test paths that should not be ignored
        assert not manager._should_ignore_gcs_path("prompt.yaml")
        assert not manager._should_ignore_gcs_path("config.json")
        assert not manager._should_ignore_gcs_path("subdir/prompt.yaml")


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_abstract_method_not_implemented(self):
        """Test that abstract method raises NotImplementedError."""

        # Create instance of abstract class directly (shouldn't be done in practice)
        class IncompleteManager(VersionManager):
            pass

        with pytest.raises(TypeError):
            IncompleteManager()

    def test_yaml_parsing_error(self, version_manager_gcs):
        """Test handling of invalid YAML content."""
        # Mock invalid YAML content
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.exists.return_value = True
        version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.download_as_text.return_value = "invalid: yaml: content: ["

        with pytest.raises(yaml.YAMLError):
            version_manager_gcs.load_prompt(["test", "prompt"], version="1.0.0")

    def test_file_permission_error(self, version_manager_local):
        """Test handling of file permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                version_manager_local.load_prompt(["generic", "metric_1"])


class TestPrivateMethods:
    """Test private helper methods."""

    def test_download_gcs_to_dir(self, version_manager_gcs):
        """Test downloading GCS content to local directory."""
        mock_blobs = [
            Mock(),
            Mock(),
            Mock(),  # Directory marker
        ]

        # Set proper name attributes
        mock_blobs[0].name = "test-prompts/Version 1.0.0/generic/metric_1.yaml"
        mock_blobs[
            1
        ].name = "test-prompts/Version 1.0.0/customized/brand_1/metric_1.yaml"
        mock_blobs[2].name = "test-prompts/Version 1.0.0/"  # Directory marker

        # Configure mock blobs
        for blob in mock_blobs:
            blob.download_to_filename = Mock()

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)

            version_manager_gcs._download_gcs_to_dir("1.0.0", target_dir)

            # Verify download_to_filename was called for non-directory blobs
            assert mock_blobs[0].download_to_filename.called
            assert mock_blobs[1].download_to_filename.called
            assert not mock_blobs[2].download_to_filename.called  # Directory marker

    def test_upload_dir_to_gcs(self, version_manager_gcs):
        """Test uploading local directory to GCS."""
        mock_files = [
            Mock(spec=Path),
            Mock(spec=Path),  # Directory
        ]

        # Configure mock files
        mock_files[0].is_file.return_value = True
        mock_files[0].relative_to.return_value = Path("generic/metric_1.yaml")
        mock_files[1].is_file.return_value = False  # Directory

        with patch("pathlib.Path.rglob", return_value=mock_files):
            version_manager_gcs._upload_dir_to_gcs("1.0.0")

            # Should only upload files, not directories
            assert (
                version_manager_gcs._gcs_client.bucket.return_value.blob.call_count == 1
            )
            assert (
                version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.upload_from_filename.call_count
                == 1
            )

    def test_upload_dir_to_gcs_with_ignore_files(self, version_manager_gcs):
        """Test uploading local directory to GCS with ignore patterns."""
        # Configure version manager with ignore patterns
        version_manager_gcs.ignore_files = ["*.log", "*.tmp", "cache/*"]

        mock_files = [
            Mock(spec=Path),  # YAML file (should upload)
            Mock(spec=Path),  # Log file (should ignore)
            Mock(spec=Path),  # Tmp file (should ignore)
            Mock(spec=Path),  # Cache file (should ignore)
            Mock(spec=Path),  # Directory (should skip)
        ]

        # Configure mock files
        mock_files[0].is_file.return_value = True
        mock_files[0].relative_to.return_value = Path("generic/metric_1.yaml")
        mock_files[1].is_file.return_value = True
        mock_files[1].relative_to.return_value = Path("debug.log")
        mock_files[2].is_file.return_value = True
        mock_files[2].relative_to.return_value = Path("temp.tmp")
        mock_files[3].is_file.return_value = True
        mock_files[3].relative_to.return_value = Path("cache/data.yaml")
        mock_files[4].is_file.return_value = False  # Directory

        with patch("pathlib.Path.rglob", return_value=mock_files):
            version_manager_gcs._upload_dir_to_gcs("1.0.0")

            # Should only upload the YAML file (1 file), ignoring log, tmp, and cache files
            assert (
                version_manager_gcs._gcs_client.bucket.return_value.blob.call_count == 1
            )
            assert (
                version_manager_gcs._gcs_client.bucket.return_value.blob.return_value.upload_from_filename.call_count
                == 1
            )

            # Verify the correct file was uploaded
            version_manager_gcs._gcs_client.bucket.return_value.blob.assert_called_with(
                "test-prompts/Version 1.0.0/generic/metric_1.yaml"
            )

    def test_download_gcs_to_dir_with_ignore_files(self, version_manager_gcs):
        """Test downloading GCS content to local directory with ignore patterns."""
        # Configure version manager with ignore patterns
        version_manager_gcs.ignore_files = ["*.log", "*.tmp", "cache/*"]

        mock_blobs = [
            Mock(),  # YAML file (should download)
            Mock(),  # Log file (should ignore)
            Mock(),  # Tmp file (should ignore)
            Mock(),  # Cache file (should ignore)
            Mock(),  # Directory marker (should skip)
        ]

        # Set proper name attributes
        mock_blobs[0].name = "test-prompts/Version 1.0.0/generic/metric_1.yaml"
        mock_blobs[1].name = "test-prompts/Version 1.0.0/debug.log"
        mock_blobs[2].name = "test-prompts/Version 1.0.0/temp.tmp"
        mock_blobs[3].name = "test-prompts/Version 1.0.0/cache/data.yaml"
        mock_blobs[4].name = "test-prompts/Version 1.0.0/"  # Directory marker

        # Configure mock blobs
        for blob in mock_blobs:
            blob.download_to_filename = Mock()

        version_manager_gcs._gcs_client.bucket.return_value.list_blobs.return_value = (
            mock_blobs
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)

            version_manager_gcs._download_gcs_to_dir("1.0.0", target_dir)

            # Verify only the YAML file was downloaded (ignored log, tmp, cache files)
            assert mock_blobs[0].download_to_filename.called  # YAML file
            assert not mock_blobs[1].download_to_filename.called  # Log file (ignored)
            assert not mock_blobs[2].download_to_filename.called  # Tmp file (ignored)
            assert not mock_blobs[3].download_to_filename.called  # Cache file (ignored)
            assert not mock_blobs[4].download_to_filename.called  # Directory marker

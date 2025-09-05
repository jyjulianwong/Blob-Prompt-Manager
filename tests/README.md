# Tests for Blob Storage Prompt Manager

This directory contains comprehensive unit tests for the `PromptManager` class using pytest.

## Test Structure

- **`conftest.py`**: Contains pytest fixtures and a concrete implementation of the abstract `PromptManager` class for testing
- **`test_prompt_manager.py`**: Main test suite with comprehensive test coverage

## Test Coverage

The test suite covers the following areas:

### 1. Initialization (`TestPromptManagerInit`)
- Local-only initialization
- GCS configuration with and without credentials
- Parameter validation

### 2. Local Prompt Operations (`TestLocalPromptOperations`)
- Loading prompts from local files
- Loading customized vs generic prompts
- String representation of prompts
- Field extraction from prompts
- Error handling for missing files and fields

### 3. GCS Prompt Operations (`TestGCSPromptOperations`)
- Loading prompts from GCS with proper mocking
- Version-specific loading
- Latest version loading
- Error handling for missing prompts and configurations

### 4. Version Management (`TestVersionManagement`)
- Listing available versions
- Version sorting and validation
- Next version calculation for different bump types
- Handling invalid version formats

### 5. Snapshot Operations (`TestSnapshotOperations`)
- Saving snapshots to GCS
- Loading snapshots from GCS
- Replace vs. new directory options
- Latest version handling
- Error handling for various edge cases

### 6. Error Handling (`TestErrorHandling`)
- Abstract method implementation checking
- YAML parsing errors
- File permission errors
- Configuration validation

### 7. Private Methods (`TestPrivateMethods`)
- GCS upload and download operations
- File system interactions

## Mocking Strategy

The tests use comprehensive mocking for:

- **Google Cloud Storage operations**: All GCS client interactions are mocked to avoid actual cloud calls
- **File system operations**: Path operations are mocked where needed to avoid filesystem dependencies
- **External dependencies**: YAML parsing errors and permission errors are simulated

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test class
pytest tests/test_prompt_manager.py::TestLocalPromptOperations -v

# Run with coverage (if installed)
pytest tests/ --cov=blob_prompt_manager
```

## Test Fixtures

Key fixtures provided in `conftest.py`:

- `temp_prompts_dir`: Creates a temporary directory with sample YAML files
- `mock_gcs_client`: Provides a mocked GCS client with common operations
- `prompt_manager_local`: PromptManager instance configured for local operations
- `prompt_manager_gcs`: PromptManager instance configured with mocked GCS
- `sample_yaml_content`: Sample YAML content for testing

## Test Data

The test suite uses realistic sample data that mirrors the structure expected by the PromptManager:

```yaml
metric_1:
  description: "This is a generic prompt."
  synonyms:
    - "Metric 1"
    - "metric 1"
    - "metric-1"
  extraction_instructions: |
    "Extract the following information from the text: [information]"
```

This ensures tests are realistic and catch real-world issues.

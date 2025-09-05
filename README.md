# Blob-Prompt-Manager

A Python class for managing prompts from local directories and Google Cloud Storage with versioning support.

## Overview

The `PromptManager` is an abstract base class that provides functionality to:
- Load prompts from local YAML files
- Save snapshots of local prompts to Google Cloud Storage with semantic versioning
- Load prompts from specific versions stored in GCS
- Manage prompt versions with automatic version bumping

## Key Features

- **Abstract Design**: Implement the `get_prompt_file_path()` method to define your prompt organization
- **Local & Cloud Storage**: Seamlessly switch between local development and versioned cloud storage
- **Semantic Versioning**: Automatic version bumping (major, minor, patch) for prompt snapshots
- **YAML Support**: Built-in parsing and formatting of YAML prompt files
- **Flexible Structure**: Support any directory structure through custom path mapping

## Quick Start

### 1. Implement the Abstract Method

```python
from blob_prompt_manager import PromptManager
from typing import List

class MyPromptManager(PromptManager):
    def get_prompt_file_path(self, keys: List[str]) -> str:
        """Map keys to file paths relative to prompts/ directory."""
        brand, metric = keys
        if brand.lower() == "generic":
            return f"generic/{metric.lower()}.yaml"
        else:
            return f"customized/{brand.lower()}/{metric.lower()}.yaml"
```

### 2. Basic Usage

```python
# Initialize (local only)
manager = MyPromptManager(local_dir_path="prompts")

# Load from local directory
prompt = manager.load_prompt(keys=["Goldman Sachs", "TVPI"], version="local")

# Initialize with GCS support
manager = MyPromptManager(
    local_dir_path="prompts"
    gcs_bucket_name="my-prompts-bucket",
    gcs_dir_path="prompt-artifacts",
)

# Save snapshot to GCS
new_version = manager.save_snapshot(next_version_bump="major")  # Creates "Version 1.0.0"

# Load from specific version
prompt = manager.load_prompt(keys=["Goldman Sachs", "TVPI"], version="1.0.0")
```

## API Reference

### PromptManager Class

#### Constructor Parameters

- `gcs_bucket_name` (str, optional): Google Cloud Storage bucket name
- `gcs_dir_path` (str, optional): Path within GCS bucket for storing versions
- `local_dir_path` (str): Local directory containing prompts (default: "prompts")
- `gcs_credentials_path` (str, optional): Path to GCS service account JSON

#### Methods

**`load_prompt(keys: List[str], version: str = "local") -> Dict[str, Any]`**
- Load a prompt from local directory or specific GCS version
- Returns parsed YAML content as dictionary

**`save_snapshot(next_version_bump: Literal["major", "minor", "patch"] = "major") -> str`**
- Save local prompts to GCS with version bumping
- Returns the new version number created

**`list_versions() -> List[str]`**
- List all available versions in GCS (sorted descending)

**`get_prompt_as_string(keys: List[str], version: str = "local", field: Optional[str] = None) -> str`**
- Get prompt as formatted string, optionally extracting specific field

**`get_prompt_file_path(keys: List[str]) -> str` (Abstract)**
- **Must be implemented**: Map keys to file path relative to prompts/ directory

## Examples

### Brand-Metric Organization

```python
from blob_prompt_manager import BrandMetricPromptManager

manager = BrandMetricPromptManager(
    gcs_bucket_name="my-bucket",
    gcs_dir_path="prompts"
)

# Maps to: customized/goldman_sachs/tvpi.yaml
prompt = manager.load_prompt(["Goldman Sachs", "TVPI"], version="local")

# Maps to: generic/tvpi.yaml  
generic = manager.load_prompt(["Generic", "TVPI"], version="local")
```

### Hierarchical Organization

```python
from blob_prompt_manager import HierarchicalPromptManager

manager = HierarchicalPromptManager()

# Maps to: finance/metrics/tvpi.yaml
prompt = manager.load_prompt(["finance", "metrics", "tvpi"])

# Maps to: marketing/campaigns.yaml
prompt = manager.load_prompt(["marketing", "campaigns"])
```

## Directory Structure

Your prompts directory should contain YAML files organized however you prefer:

```
prompts/
├── generic/
│   └── metric_1.yaml
└── customized/
    ├── brand_1/
    │   └── metric_1.yaml
    ├── brand_2/
    │   └── metric_1.yaml
    └── brand_3/
        └── metric_1.yaml
```

## GCS Versioning

When you call `save_snapshot()`, the entire local prompts directory is uploaded to GCS under a version folder:

```
gs://your-bucket/prompt-artifacts/
├── Version 1.0.0/
│   ├── generic/
│   │   └── metric_1.yaml
│   └── customized/
│       └── brand_1/
│           └── metric_1.yaml
└── Version 1.1.0/
    └── ...
```

## Get started with development

1. Clone the repository.

```bash
git clone https://github.com/jyjulianwong/Blob-Prompt-Manager.git
```

2. Verify that you have a compatible Python version installed on your machine.
```bash
python --version
```

3. Install [uv](https://github.com/astral-sh/uv) (used as the package manager for this project).

4. Install the development dependencies.
```bash
cd Blob-Prompt-Manager/
uv sync --all-groups
uv run pre-commit install
```

5. Run the demo script.
```bash
uv run blob_prompt_manager/demo.py
```

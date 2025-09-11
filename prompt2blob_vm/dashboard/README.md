# Prompt2Blob Version Manager Dashboard

A comprehensive Streamlit-based web interface for managing and viewing prompt versions from both local files and Google Cloud Storage.

## Features

### Comprehensive Dashboard (`app.py`)
- 📁 **File Browser**: Browse local and GCS prompt files with version selection
- 🔍 **Advanced Search**: Search files by name or path
- 🌳 **Tree View**: Hierarchical file browser
- 📄 **YAML Editor**: View and edit prompt files with syntax highlighting
- 📝 **Structured Preview**: JSON preview of YAML content
- 💾 **Save Changes**: Edit and save local files directly
- 🔄 **Version Management**: Create snapshots and load versions from GCS
- 🔄 **Version Comparison**: Compare files between different versions
- 📊 **Statistics**: File counts, sizes, and metadata
- ⚙️ **Enhanced Configuration**: Collapsible settings panel

## Quick Start

### 1. Install Dependencies
```bash
cd Prompt2Blob-VM/
uv sync --all-groups
```

### 2. Launch Dashboard

#### From Dashboard Directory
```bash
cd prompt2blob_vm/dashboard/
uv run runner.py
```

#### Custom Port
```bash
uv run runner.py --port 8502
```

#### Programmatic Launch
```bash
uv run runner_demo.py
```

### 3. Configure Settings

In the sidebar, configure:
- **Local Directory**: Path to your local prompts folder
- **GCS Settings** (optional):
  - Bucket name
  - Directory path within bucket
  - Service account credentials path

## Usage

### Local File Management
1. Select "local" version in the file browser
2. Choose a file from the dropdown or tree view
3. Edit content in the YAML editor
4. Click "Save Changes" to persist modifications

### GCS Integration
1. Configure GCS settings in the sidebar
2. Select a version from the dropdown
3. Browse and view files from that version
4. Use version management to create snapshots or load versions

### Version Management
- **Save Snapshot**: Create a new version in GCS with local files
- **Load Version**: Download a GCS version to replace local files
- **Compare Versions**: See differences between versions

## File Structure

```
prompt2blob_vm/dashboard/
├── __init__.py              # Module initialization
├── app.py                   # Comprehensive dashboard with all features
├── file_explorer.py            # GCS integration utilities
├── runner.py         # CLI launcher script
├── runner_demo.py        # Programmatic launcher
└── README.md               # This file
```

## Configuration

### Environment Variables
You can set these environment variables for default configuration:
- `PROMPTS_LOCAL_DIR`: Default local directory
- `PROMPTS_GCS_BUCKET`: Default GCS bucket name
- `PROMPTS_GCS_DIR`: Default GCS directory path
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCS credentials

### GCS Authentication
The dashboard supports multiple authentication methods:
1. **Service Account Key**: Provide path to JSON key file
2. **Default Credentials**: Use `gcloud auth application-default login`
3. **Environment Variable**: Set `GOOGLE_APPLICATION_CREDENTIALS`

## Troubleshooting

### Common Issues

1. **"GCS configuration required"**
   - Ensure bucket name and directory path are provided
   - Check GCS credentials are valid

2. **"File not found"**
   - Verify local directory path exists
   - Check file permissions

3. **"Error loading version"**
   - Confirm GCS bucket and version exist
   - Validate authentication credentials

### Debug Mode
Run with debug logging:
```bash
streamlit run enhanced_app.py --logger.level=debug
```

## Development

### Adding New Features
1. Create utility functions in `file_explorer.py`
2. Add UI components to dashboard classes
3. Update session state management as needed
4. Test with both local and GCS configurations

### Custom Prompt Managers
The dashboard works with any `VersionManager` subclass. To use a custom implementation:

```python
from your_module import CustomPromptManager
from prompt2blob_vm.dashboard.app import PromptDashboard

class CustomDashboard(PromptDashboard):
    def _init_prompt_manager(self):
        # Initialize with your custom manager
        self.version_manager = CustomPromptManager(...)
```

## API Reference

### PromptDashboard
Basic dashboard implementation with core features.

### EnhancedPromptDashboard
Advanced dashboard with additional features:
- Search and filtering
- Tree view navigation
- Version comparison
- Enhanced statistics

### GCSFileExplorer
Utility class for enhanced GCS operations:
- `list_files_in_version()`: Get files in a specific version
- `get_version_metadata()`: Get version statistics
- `compare_versions()`: Compare files between versions

### LocalFileExplorer
Utility class for local file operations:
- `get_file_tree()`: Get hierarchical file structure
- `search_files()`: Search files by query
- `get_file_stats()`: Get local file statistics

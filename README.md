# Blob-Storage-Prompt-Manager

## Get started with development

1. Clone the repository.

```bash
git clone https://github.com/jyjulianwong/Blob-Storage-Prompt-Manager.git
```

2. Verify that you have a compatible Python version installed on your machine.
```bash
python --version
```

3. Install [uv](https://github.com/astral-sh/uv) (used as the package manager for this project).

4. Install the development dependencies.
```bash
cd Blob-Storage-Prompt-Manager/
uv sync --all-groups
uv run pre-commit install
```

5. Run the demo script.
```bash
uv run blob_storage_prompt_manager/demo.py
```

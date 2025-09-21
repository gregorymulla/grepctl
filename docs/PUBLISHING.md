# Publishing grepctl to PyPI

This guide explains how to build and publish the grepctl package to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at [https://pypi.org](https://pypi.org)
2. **API Token**: Generate an API token from your PyPI account settings
3. **Test PyPI (Optional)**: Create an account at [https://test.pypi.org](https://test.pypi.org) for testing

## Setup

### 1. Install Build Tools

```bash
pip install --upgrade pip
pip install --upgrade build twine
```

### 2. Configure PyPI Credentials

Create a `~/.pypirc` file (see `.pypirc.example` for template):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-API-TOKEN-HERE
```

**Security Note**: Keep your `.pypirc` file secure with proper permissions:
```bash
chmod 600 ~/.pypirc
```

## Building the Package

### 1. Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 2. Build Distribution Packages

```bash
python -m build
```

This creates:
- `dist/grepctl-0.1.0.tar.gz` (source distribution)
- `dist/grepctl-0.1.0-py3-none-any.whl` (wheel distribution)

### 3. Verify Package Contents

```bash
# Check the tarball contents
tar -tzf dist/grepctl-0.1.0.tar.gz | head -20

# Check wheel contents
unzip -l dist/grepctl-0.1.0-py3-none-any.whl | head -20
```

## Testing (Recommended)

### 1. Test Locally

Create a virtual environment and test installation:

```bash
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install dist/grepctl-0.1.0-py3-none-any.whl

# Test the CLI
grepctl --help

# Cleanup
deactivate
rm -rf test_env
```

### 2. Upload to Test PyPI

```bash
python -m twine upload --repository testpypi dist/*
```

### 3. Install from Test PyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ grepctl
```

## Publishing to PyPI

### 1. Upload to PyPI

```bash
python -m twine upload dist/*
```

### 2. Verify Upload

Visit your package at: https://pypi.org/project/grepctl/

### 3. Install from PyPI

```bash
pip install grepctl
```

## Post-Publication

### Installation Methods

Users can install the package using:

```bash
# Basic installation
pip install grepctl

# With multimedia support
pip install grepctl[multimedia]

# With development tools
pip install grepctl[dev]

# With research extras
pip install grepctl[research]

# All extras
pip install grepctl[multimedia,dev,research]
```

### Usage After Installation

```bash
# Main CLI
grepctl --help
grepctl search "your query"
grepctl ingest --bucket your-bucket

# Management tool
grepctl --help
grepctl init all --bucket your-bucket --auto-ingest
grepctl status
grepctl search "your query"
```

## Version Management

### Updating Version

1. Update version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Update `CHANGELOG.md` with release notes

3. Create git tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. Build and publish new version

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify your API token is correct
   - Ensure token starts with `pypi-`
   - Check token permissions

2. **Package Name Taken**
   - Choose a different name in `pyproject.toml`
   - Check availability at https://pypi.org/project/YOUR-NAME/

3. **Missing Files**
   - Check `MANIFEST.in` includes all necessary files
   - Verify files exist in the repository

4. **Import Errors**
   - Ensure all dependencies are listed in `pyproject.toml`
   - Test installation in clean environment

### Getting Help

- PyPI Documentation: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/
- Python Packaging Guide: https://packaging.python.org/en/latest/tutorials/packaging-projects/

## Continuous Integration

For automated publishing, you can use GitHub Actions:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Remember to add `PYPI_API_TOKEN` to your GitHub repository secrets.
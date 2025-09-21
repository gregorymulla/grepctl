# Quick Start: Publishing grepctl to PyPI

## 🚀 Fast Track (5 minutes)

### 1. Install Tools
```bash
pip install --upgrade build twine
```

### 2. Build Package
```bash
python -m build
```

### 3. Test Locally (Optional but Recommended)
```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install and test
pip install dist/*.whl
grepctl --help
grepctl --help

# Cleanup
deactivate && rm -rf test_env
```

### 4. Publish to TestPyPI First (Recommended)
```bash
# Upload to test repository
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ grepctl
```

### 5. Publish to PyPI
```bash
# Upload to production PyPI
python -m twine upload dist/*
```

## 📋 Pre-Publication Checklist

- [ ] PyPI account created at https://pypi.org
- [ ] API token generated (Account Settings → API tokens)
- [ ] Version number updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md is complete and renders correctly
- [ ] All tests pass (if applicable)
- [ ] Package builds without errors

## 🔑 Authentication Setup

### Option 1: Interactive (Easiest)
```bash
# Twine will prompt for username and password
# Username: __token__
# Password: pypi-YOUR-API-TOKEN-HERE
python -m twine upload dist/*
```

### Option 2: Environment Variables
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR-API-TOKEN-HERE
python -m twine upload dist/*
```

### Option 3: Config File (~/.pypirc)
```ini
[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE
```

## 📦 After Publishing

Your package will be available at:
- **PyPI Page**: https://pypi.org/project/grepctl/
- **Installation**: `pip install grepctl`

### Installation Options:
```bash
# Basic
pip install grepctl

# With extras
pip install grepctl[multimedia]  # Image/video processing
pip install grepctl[dev]         # Development tools
pip install grepctl[research]    # Research datasets
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid or non-existent authentication" | Check API token starts with `pypi-` |
| "Package name already exists" | Choose different name in pyproject.toml |
| "Invalid distribution file" | Run `twine check dist/*` to validate |
| "Missing metadata" | Ensure pyproject.toml has all required fields |

## 📚 Resources

- **Full Guide**: See `PUBLISHING.md` for detailed instructions
- **PyPI Help**: https://pypi.org/help/
- **Packaging Guide**: https://packaging.python.org/

---

**Ready to publish?** Just run:
```bash
python -m build && python -m twine upload dist/*
```
#!/bin/bash
# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Upload to TestPyPI
echo "Uploading to TestPyPI..."
uv run twine upload --repository testpypi dist/*

echo "Upload complete!"
echo "View at: https://test.pypi.org/project/grepctl/"
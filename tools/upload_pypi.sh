#!/bin/bash
# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Upload to PyPI (production)
echo "Uploading to PyPI (production)..."
uv run twine upload dist/*

echo "Upload complete!"
echo "View at: https://pypi.org/project/grepctl/"
echo "Install with: pip install grepctl"
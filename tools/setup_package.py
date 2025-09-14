#!/usr/bin/env python3
"""
Script to prepare the grepctl package for PyPI publishing.
This reorganizes the code to work as a standalone package.
"""

import os
import shutil
from pathlib import Path

def setup_grepctl_package():
    """Reorganize files for grepctl package structure."""

    print("Setting up grepctl package structure...")

    # Create package directory if it doesn't exist
    package_dir = Path("grepctl_package")
    package_dir.mkdir(exist_ok=True)

    # Create source directory
    src_dir = package_dir / "src" / "grepctl"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Copy main grepctl.py to package
    if Path("grepctl.py").exists():
        shutil.copy2("grepctl.py", src_dir / "__main__.py")
        shutil.copy2("grepctl.py", src_dir / "cli.py")
        print("✓ Copied grepctl.py to package")

    # Create __init__.py
    init_content = '''"""
grepctl - One-command orchestration for multimodal semantic search in BigQuery.
"""

__version__ = "0.1.0"

from .cli import cli

__all__ = ['cli', '__version__']
'''
    (src_dir / "__init__.py").write_text(init_content)
    print("✓ Created __init__.py")

    # Copy supporting files
    files_to_copy = [
        ("pyproject.toml", package_dir / "pyproject.toml"),
        ("README_PYPI.md", package_dir / "README.md"),
        ("LICENSE", package_dir / "LICENSE"),
        ("CHANGELOG.md", package_dir / "CHANGELOG.md"),
        ("MANIFEST.in", package_dir / "MANIFEST.in"),
        (".grepctl.yaml.example", package_dir / ".grepctl.yaml.example"),
        ("config.yaml.example", package_dir / "config.yaml.example"),
    ]

    for src, dst in files_to_copy:
        if Path(src).exists():
            shutil.copy2(src, dst)
            print(f"✓ Copied {src}")

    # Copy documentation
    docs_dir = package_dir / "docs"
    docs_dir.mkdir(exist_ok=True)

    doc_files = [
        "grepctl_README.md",
        "grepctl_technical_paper.md",
        "lessons_learned.md",
        "PUBLISHING.md",
        "PYPI_QUICKSTART.md"
    ]

    for doc in doc_files:
        if Path(doc).exists():
            shutil.copy2(doc, docs_dir / doc)
            print(f"✓ Copied documentation: {doc}")

    # Copy example scripts to examples directory
    examples_dir = package_dir / "examples"
    examples_dir.mkdir(exist_ok=True)

    # Create example configuration
    example_config = '''# Example grepctl configuration
project_id: your-project-id
dataset: mmgrep
bucket: your-gcs-bucket
location: US
batch_size: 100
chunk_size: 1000
chunk_overlap: 200
vertex_connection: vertex-ai-connection
'''
    (examples_dir / "config.yaml").write_text(example_config)

    # Create example usage script
    example_usage = '''#!/usr/bin/env python3
"""
Example usage of grepctl for BigQuery semantic search.
"""

import subprocess
import sys

def run_command(cmd):
    """Run a grepctl command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}", file=sys.stderr)
    return result.returncode == 0

def main():
    """Demonstrate grepctl usage."""

    print("=" * 60)
    print("grepctl Example Usage")
    print("=" * 60)

    # Check status
    print("\\n1. Checking system status...")
    run_command("grepctl status")

    # Initialize system (commented out to prevent accidental runs)
    print("\\n2. Initialize system (uncomment to run):")
    print("   # grepctl init all --bucket your-bucket --auto-ingest")

    # Search example
    print("\\n3. Search example:")
    run_command('grepctl search "machine learning" -k 5')

    # Show available commands
    print("\\n4. Available commands:")
    run_command("grepctl --help")

if __name__ == "__main__":
    main()
'''
    (examples_dir / "example_usage.py").write_text(example_usage)

    print("\n" + "=" * 60)
    print("✅ Package structure created successfully!")
    print("=" * 60)
    print("\nPackage is ready in: grepctl_package/")
    print("\nNext steps:")
    print("1. cd grepctl_package")
    print("2. python -m build")
    print("3. python -m twine upload dist/*")

    return package_dir

if __name__ == "__main__":
    setup_grepctl_package()
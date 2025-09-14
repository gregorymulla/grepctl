#!/usr/bin/env python3
"""
Publish grepctl package to PyPI using credentials from .env file.
"""

import os
import sys
import subprocess
from pathlib import Path

def load_env():
    """Load environment variables from .env file."""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Error: .env file not found")
        print("Create a .env file with:")
        print("  TWINE_USERNAME=__token__")
        print("  TWINE_PASSWORD=pypi-YOUR-TOKEN-HERE")
        sys.exit(1)

    # Load .env file
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    # Verify required variables
    if not os.environ.get('TWINE_USERNAME'):
        print("❌ Error: TWINE_USERNAME not found in .env")
        sys.exit(1)

    if not os.environ.get('TWINE_PASSWORD'):
        print("❌ Error: TWINE_PASSWORD not found in .env")
        sys.exit(1)

    print("✅ Loaded PyPI credentials from .env")

def clean_build():
    """Clean previous build artifacts."""
    print("\n🧹 Cleaning previous builds...")
    dirs_to_clean = ['dist', 'build', '*.egg-info', 'src/*.egg-info']
    for pattern in dirs_to_clean:
        subprocess.run(f"rm -rf {pattern}", shell=True, capture_output=True)
    print("✅ Cleaned build directories")

def build_package():
    """Build the package distributions."""
    print("\n📦 Building package...")
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Build failed:")
        print(result.stderr)
        sys.exit(1)

    print("✅ Package built successfully")

    # List built files
    dist_files = list(Path('dist').glob('*'))
    print("\n📋 Built distributions:")
    for f in dist_files:
        size = f.stat().st_size / 1024  # KB
        print(f"  - {f.name} ({size:.1f} KB)")

def check_package():
    """Check package with twine."""
    print("\n🔍 Checking package...")
    result = subprocess.run(
        [sys.executable, "-m", "twine", "check", "dist/*"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("⚠️ Package check warnings:")
        print(result.stderr)
    else:
        print("✅ Package validation passed")

def upload_to_pypi(test=False):
    """Upload package to PyPI or TestPyPI."""
    repo_name = "TestPyPI" if test else "PyPI"
    print(f"\n📤 Uploading to {repo_name}...")

    cmd = [sys.executable, "-m", "twine", "upload"]

    if test:
        cmd.extend(["--repository", "testpypi"])

    cmd.append("dist/*")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Upload to {repo_name} failed:")
        print(result.stderr)
        sys.exit(1)

    print(f"✅ Successfully uploaded to {repo_name}!")

    # Show package URL
    package_name = "grepctl"
    if test:
        url = f"https://test.pypi.org/project/{package_name}/"
    else:
        url = f"https://pypi.org/project/{package_name}/"

    print(f"\n🌐 View your package at: {url}")

    # Show installation command
    if test:
        print(f"\n📥 Install from TestPyPI:")
        print(f"  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ {package_name}")
    else:
        print(f"\n📥 Install from PyPI:")
        print(f"  pip install {package_name}")

def main():
    """Main publishing workflow."""
    print("=" * 60)
    print("🚀 grepctl Package Publisher")
    print("=" * 60)

    # Check for required tools
    print("\n🔧 Checking required tools...")
    for tool in ["build", "twine"]:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", tool],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"📦 Installing {tool}...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", tool])

    # Load credentials
    load_env()

    # Clean and build
    clean_build()
    build_package()
    check_package()

    # Ask user about TestPyPI
    print("\n" + "=" * 60)
    response = input("📝 Upload to TestPyPI first? (recommended) [Y/n]: ").strip().lower()

    if response != 'n':
        upload_to_pypi(test=True)
        print("\n" + "=" * 60)
        response = input("📝 Now upload to production PyPI? [Y/n]: ").strip().lower()
        if response != 'n':
            upload_to_pypi(test=False)
    else:
        upload_to_pypi(test=False)

    print("\n" + "=" * 60)
    print("🎉 Publishing complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Publishing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
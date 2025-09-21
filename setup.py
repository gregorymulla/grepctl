#!/usr/bin/env python3
"""
Setup script for grepctl package.
This file is optional but included for compatibility with older tools.
The main configuration is in pyproject.toml.
"""

from setuptools import setup

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Setup is configured in pyproject.toml
# This file exists for backward compatibility
setup(
    long_description=long_description,
    long_description_content_type="text/markdown",
)
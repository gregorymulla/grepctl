# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`grepctl` is a Python package managed by uv. The package is structured using the standard src-layout pattern.

## Development Environment

- **Python Version**: 3.11 (specified in `.python-version`)
- **Package Manager**: uv 0.8.3+
- **Package Structure**: src-layout with package code in `src/grepctl/`

## Common Commands

### Package Management
```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Add a development dependency
uv add --dev <package>

# Run the package
uv run grepctl
```

### Development
```bash
# Run Python code with the package environment
uv run python <script.py>

# Install package in development mode
uv pip install -e .
```

## Project Structure

The package follows the standard Python src-layout:
- `src/grepctl/` - Main package source code
- `pyproject.toml` - Package configuration and dependencies
- Entry point: `grepctl:main` (configured in pyproject.toml)
- this repo is managed with uv. always use uv add. do not use pip install.
- when you push the package to pypi, make sure to bum the version. also credentials are in .env
#!/usr/bin/env python3
"""
grepctl CLI module - can be imported from grepctl package.
This is a wrapper to make grepctl available as part of the package.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import the main grepctl
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from grepctl import cli
except ImportError:
    # Fallback: try to import from package location
    import click

    @click.group()
    def cli():
        """grepctl - Manage BigQuery Semantic Grep system."""
        click.echo("Error: grepctl module not found. Please ensure the package is properly installed.")
        sys.exit(1)

if __name__ == "__main__":
    cli()
"""
API module for grepctl REST server.
"""

from .server import app, create_app

__all__ = ['app', 'create_app']
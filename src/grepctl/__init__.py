"""
BigQuery Semantic Grep - SQL-native semantic search across heterogeneous data.
"""

__version__ = "0.1.0"

from .cli import main
from .search_api import SearchClient, search

__all__ = ['main', 'SearchClient', 'search', '__version__']

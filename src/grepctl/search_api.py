"""
Simple Python API for grepctl search functionality.

Usage:
    from grepctl import SearchClient

    client = SearchClient()
    results = client.search("machine learning")

    for result in results:
        print(f"Score: {result['score']:.3f} - {result['content'][:100]}...")

Or use the convenience function:
    from grepctl import search

    results = search("neural networks", top_k=5)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import load_config
from .bigquery.connection import BigQueryClient
from .search.vector_search import SemanticSearch


class SearchClient:
    """Simple client for searching with grepctl."""

    def __init__(self, config_path: Optional[str] = None, project_id: Optional[str] = None):
        """
        Initialize the search client.

        Args:
            config_path: Optional path to config file. Defaults to ~/.grepctl/config.yaml
            project_id: Optional Google Cloud project ID. Overrides config if provided.
        """
        # Load configuration
        if config_path:
            self.config = load_config(Path(config_path))
        else:
            default_config = Path.home() / '.grepctl' / 'config.yaml'
            self.config = load_config(default_config)

        # Override project ID if provided
        if project_id:
            self.config.project_id = project_id

        # Initialize BigQuery client and search
        self.client = BigQueryClient(self.config)
        self.searcher = SemanticSearch(self.client, self.config)

    def search(
        self,
        query: str,
        top_k: int = 10,
        sources: Optional[List[str]] = None,
        rerank: bool = False,
        regex_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across all indexed documents using semantic search.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 10)
            sources: Optional list of source types to filter by
            rerank: Whether to use LLM reranking for better precision (default: False)
            regex_filter: Optional regex pattern to filter results
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)

        Returns:
            List of search results, each containing:
                - doc_id: Document ID
                - uri: Document URI/path
                - source: Source type
                - modality: Document modality
                - score: Relevance score (higher is better)
                - content: Text content of the match
                - metadata: Additional metadata

        Example:
            >>> client = SearchClient()
            >>> results = client.search("neural networks", top_k=5)
            >>> for r in results:
            ...     print(f"{r['score']:.3f}: {r['content'][:100]}...")
        """
        raw_results = self.searcher.search(
            query=query,
            top_k=top_k,
            source_filter=sources,
            use_rerank=rerank,
            regex_filter=regex_filter,
            start_date=start_date,
            end_date=end_date
        )

        # Format results for easier consumption
        formatted_results = []
        for result in raw_results:
            formatted_results.append({
                'doc_id': result.get('doc_id'),
                'uri': result.get('uri'),
                'source': result.get('source'),
                'modality': result.get('modality'),
                'score': result.get('rel_score') or result.get('distance', 0),
                'content': result.get('text_content', ''),
                'metadata': {
                    k: v for k, v in result.items()
                    if k not in ['doc_id', 'uri', 'source', 'modality', 'rel_score', 'distance', 'text_content']
                }
            })

        return formatted_results

    def search_simple(self, query: str, limit: int = 5) -> List[str]:
        """
        Simplified search that just returns content strings.

        Args:
            query: The search query text
            limit: Maximum number of results (default: 5)

        Returns:
            List of content strings from matching documents

        Example:
            >>> client = SearchClient()
            >>> contents = client.search_simple("transformer architecture")
            >>> for content in contents:
            ...     print(content[:200])
            ...     print("-" * 40)
        """
        results = self.search(query, top_k=limit)
        return [r['content'] for r in results]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed documents.

        Returns:
            Dictionary with statistics including:
                - document_count: Total number of documents
                - dataset_name: Name of the BigQuery dataset
                - index_status: Status of the vector index
        """
        return {
            'document_count': self.client.get_document_count(),
            'dataset_name': self.config.dataset_name,
            'index_status': self.client.get_index_status()
        }


# Convenience function for quick searches
def search(query: str, top_k: int = 10, **kwargs) -> List[Dict[str, Any]]:
    """
    Quick search function that creates a client and performs a search.

    Args:
        query: The search query text
        top_k: Number of results to return
        **kwargs: Additional arguments passed to SearchClient.search()

    Returns:
        List of search results

    Example:
        >>> from grepctl.api import search
        >>> results = search("database optimization", top_k=3)
        >>> print(f"Found {len(results)} results")
    """
    client = SearchClient()
    return client.search(query, top_k=top_k, **kwargs)


# For backwards compatibility and ease of import
__all__ = ['SearchClient', 'search']
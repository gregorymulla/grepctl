#!/usr/bin/env python3
"""
Example usage of the grepctl Search API.

This demonstrates various ways to use the SearchClient for semantic search.
"""

from grepctl.search_api import SearchClient, search


def basic_search_example():
    """Basic search with default settings."""
    print("=" * 60)
    print("BASIC SEARCH EXAMPLE")
    print("=" * 60)

    # Create a search client
    client = SearchClient()

    # Perform a simple search
    results = client.search("machine learning", top_k=3)

    print(f"\nFound {len(results)} results for 'machine learning':\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.3f}")
        print(f"   Source: {result['source']}")
        print(f"   URI: {result['uri']}")
        print(f"   Content: {result['content'][:150]}...")
        print()


def simple_search_example():
    """Using the simplified search interface."""
    print("=" * 60)
    print("SIMPLE SEARCH EXAMPLE")
    print("=" * 60)

    client = SearchClient()

    # Get just the content strings
    contents = client.search_simple("neural networks", limit=2)

    print(f"\nFound {len(contents)} results for 'neural networks':\n")

    for i, content in enumerate(contents, 1):
        print(f"{i}. {content[:200]}...")
        print("-" * 40)


def advanced_search_example():
    """Advanced search with filters and reranking."""
    print("=" * 60)
    print("ADVANCED SEARCH EXAMPLE")
    print("=" * 60)

    client = SearchClient()

    # Search with filters and reranking
    results = client.search(
        query="data processing pipeline",
        top_k=5,
        sources=["pdf", "markdown"],  # Only search PDFs and markdown files
        rerank=True,  # Use LLM reranking for better precision
        regex_filter=r"python|sql",  # Must contain python or sql
        start_date="2023-01-01",  # Only recent documents
    )

    print(f"\nFiltered search found {len(results)} results:\n")

    for result in results:
        print(f"- {result['source']}: {result['content'][:100]}...")


def quick_search_example():
    """Using the convenience function for quick searches."""
    print("=" * 60)
    print("QUICK SEARCH EXAMPLE")
    print("=" * 60)

    # One-liner search without creating a client
    results = search("database optimization", top_k=3)

    print(f"\nQuick search found {len(results)} results:\n")

    for result in results:
        print(f"- Score {result['score']:.3f}: {result['content'][:100]}...")


def stats_example():
    """Get statistics about the indexed documents."""
    print("=" * 60)
    print("STATISTICS EXAMPLE")
    print("=" * 60)

    client = SearchClient()
    stats = client.get_stats()

    print("\nSystem Statistics:")
    print(f"- Total documents: {stats['document_count']:,}")
    print(f"- Dataset name: {stats['dataset_name']}")
    print(f"- Index exists: {stats['index_status'].get('exists', False)}")
    print(f"- Last updated: {stats['index_status'].get('last_updated', 'Never')}")


def python_integration_example():
    """Example of integrating search into a Python application."""
    print("=" * 60)
    print("PYTHON INTEGRATION EXAMPLE")
    print("=" * 60)

    # Initialize client once for the application
    client = SearchClient()

    # Function to search and process results
    def find_relevant_docs(topic: str) -> list:
        """Find documents relevant to a topic."""
        results = client.search(topic, top_k=10, rerank=True)

        # Process results - filter by score threshold
        relevant = [r for r in results if r['score'] > 0.7]

        # Extract just the needed fields
        return [
            {
                'id': r['doc_id'],
                'path': r['uri'],
                'snippet': r['content'][:200]
            }
            for r in relevant
        ]

    # Use in your application
    docs = find_relevant_docs("artificial intelligence")
    print(f"\nFound {len(docs)} highly relevant documents")

    for doc in docs[:3]:
        print(f"\nDocument: {doc['path']}")
        print(f"Snippet: {doc['snippet']}...")


if __name__ == "__main__":
    import sys

    # Check if grepctl is properly configured
    try:
        # Run different examples
        examples = {
            "basic": basic_search_example,
            "simple": simple_search_example,
            "advanced": advanced_search_example,
            "quick": quick_search_example,
            "stats": stats_example,
            "integration": python_integration_example,
        }

        if len(sys.argv) > 1 and sys.argv[1] in examples:
            examples[sys.argv[1]]()
        else:
            # Run all examples
            print("\nGrepctl Search API Examples\n")
            print("Run specific example: python search_api_example.py [basic|simple|advanced|quick|stats|integration]\n")

            # Just run basic example by default
            basic_search_example()
            print("\n" + "=" * 60)
            print("Run other examples by passing the example name as argument")
            print("e.g., python search_api_example.py advanced")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure grepctl is properly configured and data is ingested.")
        print("Run: grepctl setup && grepctl ingest -b <your-bucket>")
        sys.exit(1)
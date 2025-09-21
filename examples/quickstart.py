#!/usr/bin/env python3
"""
Quick start example for BigQuery Semantic Grep.

This script demonstrates how to:
1. Setup the BigQuery environment
2. Ingest multimodal data from GCS
3. Generate embeddings
4. Perform semantic search
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.grepctl.config import Config
from src.grepctl.bigquery.connection import BigQueryClient
from src.grepctl.bigquery.schema import SchemaManager
from src.grepctl.ingestion.base import IngestionPipeline
from src.grepctl.search.vector_search import SemanticSearch


def main():
    """Run the quickstart example."""
    print("BigQuery Semantic Grep - Quick Start")
    print("=" * 50)

    # Load configuration
    print("\n1. Loading configuration...")
    config = Config()

    # Set project-specific settings
    config.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'semgrep-472018')
    config.dataset_name = 'mmgrep'
    config.gcs_bucket = 'gcm-data-lake'
    config.location = 'US'

    # Validate config
    try:
        config.validate()
        print(f"   ✓ Configuration loaded for project: {config.project_id}")
    except ValueError as e:
        print(f"   ✗ Configuration error: {e}")
        return 1

    # Create BigQuery client
    print("\n2. Connecting to BigQuery...")
    try:
        client = BigQueryClient(config)
        print(f"   ✓ Connected to BigQuery in location: {config.location}")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return 1

    # Check if dataset exists
    print("\n3. Checking dataset...")
    if client.check_dataset_exists():
        print(f"   ✓ Dataset '{config.dataset_name}' exists")
    else:
        print(f"   ! Dataset '{config.dataset_name}' not found")
        print("   Run 'grepctl setup' to create the dataset and tables")
        return 1

    # Get document statistics
    print("\n4. Getting document statistics...")
    doc_count = client.get_document_count()
    print(f"   Total documents: {doc_count:,}")

    if doc_count > 0:
        stats = client.get_document_stats()
        print(f"   Latest update: {stats.get('latest_update', 'Unknown')}")

    # Example search
    if doc_count > 0:
        print("\n5. Example semantic search...")
        searcher = SemanticSearch(client, config)

        query = "invoice processing errors onboarding"
        print(f"   Searching for: '{query}'")

        try:
            results = searcher.search(
                query=query,
                top_k=5,
                use_rerank=False
            )

            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n   Result {i}:")
                print(f"   - Source: {result.get('source', 'Unknown')}")
                print(f"   - URI: {result.get('uri', 'Unknown')[:50]}...")
                print(f"   - Distance: {result.get('distance', 0):.3f}")
                preview = result.get('text_content', '')[:100]
                print(f"   - Preview: {preview}...")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")

    print("\n" + "=" * 50)
    print("Quick start complete!")
    print("\nNext steps:")
    print("1. Run 'grepctl setup' to create tables")
    print("2. Run 'grepctl ingest --bucket gcm-data-lake' to ingest data")
    print("3. Run 'grepctl search \"your query\"' to search")

    return 0


if __name__ == "__main__":
    sys.exit(main())
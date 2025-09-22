"""
# Grepctl Search API - Jupyter Notebook Example

This file can be converted to a Jupyter notebook or run as a Python script.
It demonstrates how to use the grepctl Search API in data analysis workflows.
"""

# %% [markdown]
# # Grepctl Search API Tutorial
#
# This notebook demonstrates how to use the grepctl Search API for semantic search
# across your indexed documents in BigQuery.

# %% [markdown]
# ## 1. Installation and Setup
#
# First, make sure grepctl is installed and configured:
# ```bash
# pip install grepctl
# grepctl setup
# grepctl ingest -b your-gcs-bucket
# ```

# %%
# Import the SearchClient
from grepctl.search_api import SearchClient, search
import pandas as pd
import json

# Initialize the client
client = SearchClient()

print("SearchClient initialized successfully!")

# %% [markdown]
# ## 2. Basic Search

# %%
# Perform a simple search
query = "machine learning algorithms"
results = client.search(query, top_k=5)

print(f"Search results for: '{query}'")
print(f"Found {len(results)} results\n")

# Display results
for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result['score']:.3f}")
    print(f"   Source: {result['source']} | URI: {result['uri']}")
    print(f"   Content preview: {result['content'][:150]}...")
    print("-" * 80)

# %% [markdown]
# ## 3. Convert Results to DataFrame

# %%
# Search and convert to DataFrame for analysis
results = client.search("data analysis", top_k=20)

# Create DataFrame
df = pd.DataFrame(results)

# Display summary
print(f"Search Results Summary:")
print(f"Total results: {len(df)}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nSource distribution:")
print(df['source'].value_counts())
print(f"\nScore statistics:")
print(df['score'].describe())

# Show top results
df[['score', 'source', 'uri']].head(10)

# %% [markdown]
# ## 4. Filtered Search with Multiple Criteria

# %%
# Advanced search with filters
results = client.search(
    query="python programming",
    top_k=10,
    sources=["markdown", "text", "pdf"],  # Only specific file types
    rerank=True,  # Use AI reranking for better results
    regex_filter=r"(function|class|def)",  # Must contain code-related terms
)

print(f"Filtered search found {len(results)} results")

# Analyze results
for r in results[:3]:
    print(f"\nScore: {r['score']:.3f} | Source: {r['source']}")
    print(f"Content: {r['content'][:200]}...")

# %% [markdown]
# ## 5. Comparative Searches

# %%
# Compare search results for different queries
queries = [
    "neural networks",
    "deep learning",
    "machine learning",
    "artificial intelligence"
]

comparison_results = {}

for q in queries:
    results = client.search(q, top_k=5)
    comparison_results[q] = {
        'count': len(results),
        'avg_score': sum(r['score'] for r in results) / len(results) if results else 0,
        'sources': list(set(r['source'] for r in results))
    }

# Display comparison
comparison_df = pd.DataFrame(comparison_results).T
print("Query Comparison:")
print(comparison_df)

# %% [markdown]
# ## 6. Building a Search-Based QA System

# %%
def answer_question(question: str, context_size: int = 3) -> dict:
    """
    Simple QA system using semantic search.

    Args:
        question: The question to answer
        context_size: Number of documents to use as context

    Returns:
        Dictionary with question, contexts, and potential answer sources
    """
    # Search for relevant documents
    results = client.search(question, top_k=context_size, rerank=True)

    if not results:
        return {
            'question': question,
            'answer': 'No relevant information found.',
            'sources': []
        }

    # Compile context from top results
    contexts = []
    sources = []

    for r in results:
        contexts.append(r['content'])
        sources.append({
            'uri': r['uri'],
            'score': r['score'],
            'preview': r['content'][:200]
        })

    return {
        'question': question,
        'contexts': contexts,
        'sources': sources,
        'top_answer_source': sources[0]['uri'] if sources else None
    }

# Example usage
qa_result = answer_question("What are the main components of a transformer model?")

print(f"Question: {qa_result['question']}\n")
print(f"Top answer source: {qa_result['top_answer_source']}\n")
print("Relevant contexts found:")
for i, source in enumerate(qa_result['sources'], 1):
    print(f"\n{i}. Score: {source['score']:.3f}")
    print(f"   Source: {source['uri']}")
    print(f"   Preview: {source['preview']}...")

# %% [markdown]
# ## 7. Batch Processing Multiple Queries

# %%
# Process multiple queries efficiently
queries = [
    "database optimization techniques",
    "API design best practices",
    "cloud architecture patterns",
    "security vulnerabilities",
    "performance monitoring"
]

batch_results = {}

for query in queries:
    results = client.search_simple(query, limit=3)
    batch_results[query] = {
        'found': len(results),
        'preview': results[0][:100] if results else "No results"
    }

# Display batch results
print("Batch Query Results:")
print("=" * 80)
for query, info in batch_results.items():
    print(f"\nQuery: '{query}'")
    print(f"Found: {info['found']} results")
    print(f"Preview: {info['preview']}...")

# %% [markdown]
# ## 8. Export Results for Further Analysis

# %%
# Search and export results
export_results = client.search("data pipeline", top_k=50)

# Export to CSV
df_export = pd.DataFrame(export_results)
df_export.to_csv('search_results.csv', index=False)
print(f"Exported {len(df_export)} results to search_results.csv")

# Export to JSON for web applications
with open('search_results.json', 'w') as f:
    json.dump(export_results[:10], f, indent=2, default=str)
print("Exported top 10 results to search_results.json")

# Summary statistics
print(f"\nExport Summary:")
print(f"- Total results: {len(export_results)}")
print(f"- Unique sources: {df_export['source'].nunique()}")
print(f"- Score range: {df_export['score'].min():.3f} - {df_export['score'].max():.3f}")

# %% [markdown]
# ## 9. System Statistics

# %%
# Get system statistics
stats = client.get_stats()

print("Grepctl System Statistics")
print("=" * 40)
print(f"Total documents indexed: {stats['document_count']:,}")
print(f"Dataset: {stats['dataset_name']}")
print(f"Index status: {'Active' if stats['index_status'].get('exists') else 'Not created'}")
print(f"Last updated: {stats['index_status'].get('last_updated', 'Never')}")

# %% [markdown]
# ## 10. Quick Search Function
#
# For one-off searches without creating a client:

# %%
# Use the convenience function
from grepctl.search_api import search

quick_results = search("python async programming", top_k=3, rerank=True)

print("Quick search results:")
for i, r in enumerate(quick_results, 1):
    print(f"{i}. {r['content'][:150]}...")

# %% [markdown]
# ## Summary
#
# The grepctl Search API provides:
#
# 1. **Simple Interface**: Easy-to-use SearchClient class
# 2. **Flexible Searching**: Multiple search options and filters
# 3. **Python Integration**: Works seamlessly with pandas, numpy, etc.
# 4. **Batch Processing**: Efficient handling of multiple queries
# 5. **Export Options**: Easy export to CSV, JSON, or other formats
#
# For more information, see the [grepctl documentation](https://github.com/your-repo/grepctl).
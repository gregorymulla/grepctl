# Grepctl Search Guide

`grepctl` is a powerful semantic search tool that enables SQL-native semantic search across heterogeneous data stored in BigQuery. This guide covers how to use grepctl search from the command line, Python, and SQL.

## Overview

Grepctl uses vector embeddings and BigQuery's VECTOR_SEARCH capabilities to perform semantic search across various data types including:
- PDFs and documents
- Images with descriptions
- Audio transcriptions
- Video content (with transcripts, OCR, and visual analysis)
- Text files, markdown, JSON, CSV

## CLI Usage

### Basic Search

```bash
# Simple semantic search
grepctl search "machine learning transformers"

# Specify number of results
grepctl search "neural networks" --top-k 10

# Search with specific output format
grepctl search "data pipeline" --output json
grepctl search "kubernetes deployment" --output csv
```

### Advanced Filtering

```bash
# Filter by source type
grepctl search "architecture diagram" --sources pdf --sources images

# Use LLM reranking for better precision
grepctl search "python async programming" --rerank

# Add regex filter for additional precision
grepctl search "error handling" --regex "try.*except|catch.*error"

# Date range filtering
grepctl search "quarterly report" --start-date 2024-01-01 --end-date 2024-03-31

# Combine multiple filters
grepctl search "api documentation" \
    --sources pdf \
    --top-k 20 \
    --regex "REST|GraphQL" \
    --rerank
```

### Search Options

- `--top-k, -k`: Number of results to return (default: 20)
- `--sources, -s`: Filter by source types (can specify multiple)
- `--rerank`: Use LLM reranking for improved relevance
- `--regex, -r`: Additional regex pattern to match
- `--start-date`: Filter documents created after this date (YYYY-MM-DD)
- `--end-date`: Filter documents created before this date (YYYY-MM-DD)
- `--output, -o`: Output format (table, json, csv) (default: table)

## Python Programmatic Usage

### Installation

```python
# Install the package
# uv add grepctl
# or
# pip install grepctl
```

### Basic Usage

```python
from grepctl.config import load_config
from grepctl.bigquery.connection import BigQueryClient
from grepctl.search.vector_search import SemanticSearch

# Load configuration
config = load_config()  # Uses ~/.grepctl/config.yaml by default

# Initialize client and search
client = BigQueryClient(config)
searcher = SemanticSearch(client, config)

# Perform search
results = searcher.search(
    query="deep learning models",
    top_k=10
)

# Process results
for result in results:
    print(f"Score: {result.get('distance', 0):.3f}")
    print(f"Source: {result['source']}")
    print(f"Content: {result['text_content'][:200]}...")
    print(f"URI: {result['uri']}\n")
```

### Advanced Search

```python
# Search with filters
results = searcher.search(
    query="kubernetes deployment strategies",
    top_k=15,
    source_filter=['pdf', 'markdown'],
    use_rerank=True,
    regex_filter=r"k8s|helm|kubectl",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Find similar documents
similar_docs = searcher.search_similar(
    doc_id="doc_123456",
    top_k=5
)

# Hybrid search (semantic + keyword)
hybrid_results = searcher.hybrid_search(
    query="machine learning pipeline",  # Semantic query
    keyword_query="mlops cicd",         # Keyword query
    top_k=20,
    keyword_weight=0.3                  # 30% keyword, 70% semantic
)
```

### Custom Configuration

```python
from pathlib import Path
from grepctl.config import Config

# Create custom config
config = Config(
    project_id="your-project",
    dataset_name="your_dataset",
    location="us-central1",
    embedding_model="your-embedding-model",
    search_multiplier=3,  # Fetch 3x results for filtering
)

# Initialize with custom config
client = BigQueryClient(config)
searcher = SemanticSearch(client, config)
```

## BigQuery SQL Usage

### Direct SQL Search

```sql
-- Generate embedding for search query
WITH query_embedding AS (
    SELECT ml_generate_embedding_result AS embedding
    FROM ML.GENERATE_EMBEDDING(
        MODEL `your-project.your_dataset.text_embedding_model`,
        (SELECT 'machine learning transformers' AS content),
        STRUCT(TRUE AS flatten_json_output)
    )
)
-- Perform vector search
SELECT
    base.doc_id,
    base.uri,
    base.source,
    base.modality,
    base.text_content,
    distance AS similarity_score
FROM VECTOR_SEARCH(
    TABLE `your-project.your_dataset.search_corpus`,
    'embedding',
    (SELECT embedding FROM query_embedding),
    top_k => 10,
    distance_type => 'COSINE'
)
ORDER BY distance ASC
```

### Search with Filters

```sql
-- Search PDFs created in 2024
WITH query_embedding AS (
    SELECT ml_generate_embedding_result AS embedding
    FROM ML.GENERATE_EMBEDDING(
        MODEL `your-project.your_dataset.text_embedding_model`,
        (SELECT 'annual report financial analysis' AS content),
        STRUCT(TRUE AS flatten_json_output)
    )
)
SELECT
    base.doc_id,
    base.uri,
    base.source,
    base.created_at,
    base.text_content,
    distance
FROM VECTOR_SEARCH(
    TABLE `your-project.your_dataset.search_corpus`,
    'embedding',
    (SELECT embedding FROM query_embedding),
    top_k => 20,
    distance_type => 'COSINE'
)
WHERE base.source = 'pdf'
    AND base.created_at >= '2024-01-01'
    AND base.created_at < '2025-01-01'
ORDER BY distance ASC
LIMIT 10
```

### Hybrid Search in SQL

```sql
-- Combine vector and keyword search
WITH
-- Vector search
vector_results AS (
    SELECT
        doc_id,
        uri,
        text_content,
        distance,
        1.0 / (1.0 + distance) AS vector_score
    FROM VECTOR_SEARCH(
        TABLE `your-project.your_dataset.search_corpus`,
        'embedding',
        (SELECT ml_generate_embedding_result AS embedding
         FROM ML.GENERATE_EMBEDDING(
             MODEL `your-project.your_dataset.text_embedding_model`,
             (SELECT 'data pipeline orchestration' AS content),
             STRUCT(TRUE AS flatten_json_output)
         )),
        top_k => 50,
        distance_type => 'COSINE'
    )
),
-- Keyword search
keyword_results AS (
    SELECT
        doc_id,
        uri,
        text_content,
        (
            CAST(LOWER(text_content) LIKE '%airflow%' AS INT64) +
            CAST(LOWER(text_content) LIKE '%prefect%' AS INT64) +
            CAST(LOWER(text_content) LIKE '%dagster%' AS INT64)
        ) / 3.0 AS keyword_score
    FROM `your-project.your_dataset.search_corpus`
    WHERE LOWER(text_content) LIKE '%airflow%'
       OR LOWER(text_content) LIKE '%prefect%'
       OR LOWER(text_content) LIKE '%dagster%'
)
-- Combine results
SELECT
    COALESCE(v.doc_id, k.doc_id) AS doc_id,
    COALESCE(v.uri, k.uri) AS uri,
    COALESCE(v.text_content, k.text_content) AS text_content,
    (COALESCE(v.vector_score, 0) * 0.7 +
     COALESCE(k.keyword_score, 0) * 0.3) AS combined_score
FROM vector_results v
FULL OUTER JOIN keyword_results k
    ON v.doc_id = k.doc_id
ORDER BY combined_score DESC
LIMIT 20
```

### Creating a Search View

```sql
-- Create a reusable search view
CREATE OR REPLACE VIEW `your-project.your_dataset.search_interface` AS
WITH search_params AS (
    -- Define search parameters (can be replaced with procedures)
    SELECT
        'machine learning' AS query_text,
        20 AS result_limit
)
SELECT
    base.doc_id,
    base.uri,
    base.source,
    base.modality,
    base.created_at,
    base.text_content,
    distance AS similarity_score
FROM search_params,
VECTOR_SEARCH(
    TABLE `your-project.your_dataset.search_corpus`,
    'embedding',
    (SELECT ml_generate_embedding_result AS embedding
     FROM ML.GENERATE_EMBEDDING(
         MODEL `your-project.your_dataset.text_embedding_model`,
         (SELECT query_text AS content FROM search_params),
         STRUCT(TRUE AS flatten_json_output)
     )),
    top_k => (SELECT result_limit FROM search_params),
    distance_type => 'COSINE'
)
ORDER BY distance ASC
```

## Performance Tips

1. **Use appropriate top_k values**: Start with smaller values (10-20) and increase as needed
2. **Apply filters early**: Use source and date filters to reduce the search space
3. **Consider hybrid search**: For queries with specific keywords, hybrid search often performs better
4. **Batch operations**: When searching programmatically, batch multiple searches together
5. **Cache embeddings**: For repeated queries, consider caching the query embeddings

## Common Use Cases

### Document Discovery
```bash
grepctl search "technical specification API endpoints" --sources pdf --top-k 5
```

### Code Search
```bash
grepctl search "async function error handling" --regex "async.*await|try.*catch"
```

### Media Content Search
```bash
# Search video transcripts
grepctl search "product demo features" --sources video

# Search images by description
grepctl search "architecture diagram cloud" --sources images
```

### Compliance and Audit
```bash
grepctl search "data retention policy GDPR" \
    --sources pdf \
    --start-date 2023-01-01 \
    --rerank
```

## Troubleshooting

### No Results Found
- Check if data has been ingested: `grepctl status`
- Verify embeddings are generated: `grepctl index --update`
- Try broader search terms or reduce filters

### Slow Performance
- Reduce top_k value
- Use source filters to limit search scope
- Consider using direct SQL for complex queries

### Relevance Issues
- Enable reranking with `--rerank`
- Use hybrid search for keyword-heavy queries
- Adjust search terms to be more semantic

## Next Steps

- Set up the system: `grepctl setup`
- Ingest data: `grepctl ingest --bucket your-bucket`
- Generate embeddings: `grepctl index --update`
- Start searching: `grepctl search "your query"`
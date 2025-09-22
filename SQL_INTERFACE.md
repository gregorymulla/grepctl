# SQL Interface for Grepctl Search

## Quick Start: Semantic Search in 1 Line

```sql
-- Simple search - just pass your query text
SELECT * FROM `your-project.grepmm.search`("how to implement OAuth2 authentication")
```

Or with more control:

```sql
-- Search with custom parameters
SELECT * FROM `your-project.grepmm.semantic_search`(
    "machine learning algorithms",  -- query text
    20,                             -- top_k results
    0.7                             -- minimum relevance (0-1)
)
```

## 🎯 Smart Code Assistant - Natural Language Code Search

```sql
-- Ask natural language questions about your codebase
WITH code_search AS (
    SELECT
        relevance_score,
        source,
        REGEXP_EXTRACT(uri, r'([^/]+)$') AS filename,
        SUBSTR(text_content, 1, 500) AS code_snippet
    FROM `your-project.grepmm.semantic_search`(
        "How do I handle async errors in Python?",
        10,    -- Get top 10 results
        0.75   -- High relevance threshold
    )
    WHERE source IN ('python', 'markdown', 'text')
)
SELECT
    CONCAT('📄 ', filename) AS file,
    ROUND(relevance_score * 100, 1) AS confidence,
    code_snippet
FROM code_search
ORDER BY relevance_score DESC;
```

## 🔍 Multi-Modal Knowledge Explorer

```sql
-- Search across different media types simultaneously
WITH multimodal_search AS (
    SELECT
        source,
        modality,
        relevance_score,
        uri,
        text_content,
        CASE source
            WHEN 'pdf' THEN '📄'
            WHEN 'video' THEN '🎥'
            WHEN 'audio' THEN '🎙️'
            WHEN 'images' THEN '🖼️'
            ELSE '📝'
        END AS icon
    FROM `your-project.grepmm.semantic_search`(
        "kubernetes deployment strategies",
        30,
        0.6
    )
)
SELECT
    icon,
    source AS media_type,
    COUNT(*) AS count,
    ROUND(AVG(relevance_score), 2) AS avg_relevance,
    ARRAY_AGG(
        STRUCT(
            REGEXP_EXTRACT(uri, r'([^/]+)$') AS filename,
            relevance_score,
            SUBSTR(text_content, 1, 200) AS preview
        )
        ORDER BY relevance_score DESC
        LIMIT 3
    ) AS top_results
FROM multimodal_search
GROUP BY icon, source
ORDER BY avg_relevance DESC;
```

## 💡 RAG Context Retriever

```sql
-- Get context for Retrieval Augmented Generation
CREATE TEMP FUNCTION get_rag_context(query STRING, max_tokens INT64)
RETURNS STRING AS (
    (
        WITH context_chunks AS (
            SELECT
                text_content,
                relevance_score,
                CONCAT('[Source: ', source, ' - ',
                       REGEXP_EXTRACT(uri, r'([^/]+)$'), ']\n') AS metadata,
                LENGTH(text_content) / 4 AS approx_tokens
            FROM `your-project.grepmm.semantic_search`(query, 15, 0.7)
        ),
        cumulative AS (
            SELECT
                text_content,
                metadata,
                relevance_score,
                SUM(approx_tokens) OVER (ORDER BY relevance_score DESC) AS running_tokens
            FROM context_chunks
        )
        SELECT STRING_AGG(
            CONCAT(metadata, text_content, '\n---\n'),
            '\n'
            ORDER BY relevance_score DESC
        )
        FROM cumulative
        WHERE running_tokens <= max_tokens
    )
);

-- Example usage for Q&A
WITH question AS (
    SELECT "How do I implement caching in Python?" AS q
)
SELECT
    q AS question,
    get_rag_context(q, 2000) AS context,
    (
        SELECT COUNT(*)
        FROM `your-project.grepmm.search`(q)
    ) AS total_matches;
```

## 🚀 Batch Search Pipeline

```sql
-- Process multiple queries efficiently
WITH queries AS (
    SELECT query FROM UNNEST([
        "authentication and authorization",
        "database optimization",
        "microservices architecture",
        "CI/CD pipelines",
        "error handling best practices"
    ]) AS query
),
batch_results AS (
    SELECT
        q.query,
        s.relevance_score,
        s.source,
        s.uri,
        s.text_content
    FROM queries q
    CROSS JOIN LATERAL (
        SELECT * FROM `your-project.grepmm.semantic_search`(q.query, 5, 0.5)
    ) s
)
SELECT
    query AS topic,
    COUNT(*) AS document_count,
    ROUND(AVG(relevance_score), 3) AS avg_relevance,
    ROUND(MAX(relevance_score), 3) AS best_match_score,
    ARRAY_AGG(DISTINCT source IGNORE NULLS) AS sources,
    SUBSTR(MAX(text_content BY relevance_score), 1, 200) AS top_result_preview
FROM batch_results
GROUP BY query
ORDER BY avg_relevance DESC;
```

## 📊 Knowledge Coverage Analysis

```sql
-- Analyze how well topics are covered in your knowledge base
WITH topic_analysis AS (
    SELECT
        "machine learning" AS topic,
        (SELECT COUNT(*) FROM `your-project.grepmm.semantic_search`("machine learning", 100, 0.6)) AS matches,
        (SELECT AVG(relevance_score) FROM `your-project.grepmm.semantic_search`("machine learning", 20, 0.6)) AS avg_score
    UNION ALL
    SELECT
        "cloud architecture",
        (SELECT COUNT(*) FROM `your-project.grepmm.semantic_search`("cloud architecture", 100, 0.6)),
        (SELECT AVG(relevance_score) FROM `your-project.grepmm.semantic_search`("cloud architecture", 20, 0.6))
    UNION ALL
    SELECT
        "data pipelines",
        (SELECT COUNT(*) FROM `your-project.grepmm.semantic_search`("data pipelines", 100, 0.6)),
        (SELECT AVG(relevance_score) FROM `your-project.grepmm.semantic_search`("data pipelines", 20, 0.6))
)
SELECT
    topic,
    matches,
    ROUND(avg_score, 3) AS avg_relevance,
    CASE
        WHEN matches = 0 THEN '❌ No coverage'
        WHEN avg_score < 0.7 THEN '⚠️ Weak coverage'
        WHEN avg_score < 0.85 THEN '✅ Good coverage'
        ELSE '🌟 Excellent coverage'
    END AS status
FROM topic_analysis
ORDER BY avg_score DESC;
```

## 🔄 Time-Based Search

```sql
-- Search with date filtering
WITH recent_docs AS (
    SELECT *
    FROM `your-project.grepmm.search_by_date`(
        "security vulnerabilities",
        DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY),  -- start_date
        CURRENT_DATE(),                               -- end_date
        20                                            -- top_k
    )
)
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS daily_mentions,
    ROUND(AVG(relevance_score), 3) AS avg_relevance,
    ARRAY_AGG(
        STRUCT(
            REGEXP_EXTRACT(uri, r'([^/]+)$') AS filename,
            relevance_score
        )
        ORDER BY relevance_score DESC
        LIMIT 3
    ) AS top_documents
FROM recent_docs
GROUP BY date
ORDER BY date DESC;
```

## 🎯 Source-Filtered Search

```sql
-- Search only specific file types
WITH filtered_results AS (
    SELECT *
    FROM `your-project.grepmm.search_by_source`(
        "REST API design",
        ["markdown", "pdf", "text"],  -- Only these sources
        15                             -- top_k
    )
)
SELECT
    source,
    COUNT(*) AS count,
    ARRAY_AGG(
        REGEXP_EXTRACT(uri, r'([^/]+)$')
        ORDER BY relevance_score DESC
        LIMIT 5
    ) AS top_files
FROM filtered_results
GROUP BY source;
```

## 📝 Simple Content Extraction

```sql
-- Get just the content strings (like search_simple in Python)
SELECT content
FROM UNNEST((
    SELECT ARRAY_AGG(text_content LIMIT 5)
    FROM `your-project.grepmm.search_content`("database optimization", 5)
)) AS content;
```

## 🔧 Quick Examples

```sql
-- One-liner search
SELECT * FROM `your-project.grepmm.search`("python async programming");

-- Search with relevance threshold
SELECT * FROM `your-project.grepmm.semantic_search`("machine learning", 10, 0.8);

-- Get just content
SELECT * FROM `your-project.grepmm.search_content`("SQL optimization", 3);

-- Search specific sources
SELECT * FROM `your-project.grepmm.search_by_source`(
    "authentication",
    ["python", "javascript"],
    10
);

-- Recent documents only
SELECT * FROM `your-project.grepmm.search_by_date`(
    "security",
    DATE('2024-01-01'),
    CURRENT_DATE(),
    20
);
```

## 📊 Advanced Analytics

```sql
-- Find similar documents (clustering)
WITH doc_sample AS (
    SELECT doc_id, embedding, uri, source
    FROM `your-project.grepmm.search_corpus`
    WHERE RAND() < 0.01  -- Sample 1% for performance
),
similarities AS (
    SELECT
        a.doc_id AS doc1,
        b.doc_id AS doc2,
        1 - COSINE_DISTANCE(a.embedding, b.embedding) AS similarity
    FROM doc_sample a
    CROSS JOIN doc_sample b
    WHERE a.doc_id < b.doc_id
        AND COSINE_DISTANCE(a.embedding, b.embedding) < 0.3
)
SELECT
    doc1,
    ARRAY_AGG(
        STRUCT(doc2, similarity)
        ORDER BY similarity DESC
        LIMIT 5
    ) AS similar_docs
FROM similarities
GROUP BY doc1;
```

## ⚙️ Setup

The search functions are automatically created when you run:

```bash
grepctl setup
```

This creates the following functions in your BigQuery dataset:

1. **`search(query)`** - Simple search with defaults
2. **`semantic_search(query, top_k, min_relevance)`** - Full control search
3. **`search_by_source(query, sources, top_k)`** - Filter by file types
4. **`search_by_date(query, start_date, end_date, top_k)`** - Date range search
5. **`search_content(query, limit)`** - Just return content strings

## 📚 Function Reference

### Core Search Functions

```sql
-- Simple search (defaults: top_k=10, min_relevance=0.0)
CALL `your-project.grepmm.search`("your query");

-- Full semantic search
CALL `your-project.grepmm.semantic_search`(
    "query text",           -- Search query
    20,                     -- Number of results
    0.7                     -- Minimum relevance (0-1)
);

-- Returns:
-- doc_id, uri, source, modality, text_content,
-- relevance_score, created_at, metadata
```

### Filtered Search Functions

```sql
-- Search by source types
CALL `your-project.grepmm.search_by_source`(
    "query",
    ["pdf", "markdown"],    -- Array of sources
    10                      -- Top K results
);

-- Search by date range
CALL `your-project.grepmm.search_by_date`(
    "query",
    DATE('2024-01-01'),     -- Start date
    CURRENT_DATE(),         -- End date
    15                      -- Top K results
);

-- Get just content
CALL `your-project.grepmm.search_content`(
    "query",
    5                       -- Limit
);
```

## 🚀 Ready to Query!

You now have powerful semantic search directly in BigQuery SQL. The functions handle all the complexity of embeddings and vector search - you just write simple SQL queries!

For Python integration, see [PYTHON_INTERFACE.md](PYTHON_INTERFACE.md).

Happy searching! 🔍
# Fix Instructions for BigQuery Semantic Grep

## Current Issues and Solutions

### 1. Vertex AI API Not Enabled

**Issue**: The system cannot generate embeddings because Vertex AI API is not enabled for the project.

**Solution**:
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project semgrep-472018

# Wait a few minutes for the API to be fully enabled
```

### 2. Create Embedding Model in BigQuery

After enabling Vertex AI, create a remote model for embeddings:

```sql
-- Create embedding model
CREATE OR REPLACE MODEL `semgrep-472018.mmgrep.text_embedding_model`
REMOTE WITH CONNECTION `semgrep-472018.US.bigquery-gcs`
OPTIONS (
  endpoint = 'text-embedding-004'
);

-- Test the model
SELECT
  ML.GENERATE_EMBEDDING(
    MODEL `semgrep-472018.mmgrep.text_embedding_model`,
    (SELECT 'test text' AS content)
  ) AS embedding_result;
```

### 3. Update Code to Use the Model

The code has been updated to handle empty embeddings correctly. Once the model is created, run:

```bash
# Generate embeddings for all documents
uv run bq-semgrep index --update

# Then rebuild the vector index
uv run bq-semgrep index --rebuild
```

### 4. Alternative: Use Keyword Search Without Embeddings

While embeddings are not available, you can still use keyword search:

```sql
-- Keyword search
SELECT
  doc_id,
  source,
  SUBSTR(text_content, 1, 500) as preview
FROM `semgrep-472018.mmgrep.search_corpus`
WHERE LOWER(text_content) LIKE '%your_search_term%'
ORDER BY created_at DESC
LIMIT 20;

-- Search with multiple keywords
SELECT
  doc_id,
  source,
  SUBSTR(text_content, 1, 500) as preview,
  (
    CASE WHEN LOWER(text_content) LIKE '%keyword1%' THEN 1 ELSE 0 END +
    CASE WHEN LOWER(text_content) LIKE '%keyword2%' THEN 1 ELSE 0 END +
    CASE WHEN LOWER(text_content) LIKE '%keyword3%' THEN 1 ELSE 0 END
  ) AS match_score
FROM `semgrep-472018.mmgrep.search_corpus`
WHERE LOWER(text_content) LIKE '%keyword1%'
   OR LOWER(text_content) LIKE '%keyword2%'
   OR LOWER(text_content) LIKE '%keyword3%'
ORDER BY match_score DESC, created_at DESC
LIMIT 20;
```

## Fixed Code Updates

The following files have been updated to handle empty embeddings:

1. **`src/bq_semgrep/bigquery/schema.py`**
   - Fixed DROP VECTOR INDEX syntax (requires ON clause)
   - Removed unsupported ivf_num_lists options

2. **`src/bq_semgrep/bigquery/queries.py`**
   - Updated embedding checks to handle empty arrays: `(embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)`

3. **`src/bq_semgrep/ingestion/embeddings.py`**
   - Updated count queries to check for empty embeddings

## Current System Status

✅ **Working Features:**
- Dataset and tables created
- 207 documents ingested (100 text + 107 markdown)
- External tables connected to GCS
- Keyword search functional
- CLI commands operational

⚠️ **Requires Vertex AI:**
- Embedding generation
- Vector index creation
- Semantic search

## Quick Test Commands

```bash
# Check system status
uv run bq-semgrep status

# Test keyword search via CLI (doesn't require embeddings)
bq query --use_legacy_sql=false "
SELECT doc_id, source, SUBSTR(text_content, 1, 200) as preview
FROM \`semgrep-472018.mmgrep.search_corpus\`
WHERE LOWER(text_content) LIKE '%love%'
LIMIT 5"

# Count documents
bq query --use_legacy_sql=false "
SELECT modality, source, COUNT(*) as count
FROM \`semgrep-472018.mmgrep.documents\`
GROUP BY modality, source"
```

## Next Steps

1. **Enable Vertex AI API** (if you want semantic search)
2. **Create embedding model** in BigQuery
3. **Generate embeddings** using the updated code
4. **Build vector index** for fast similarity search

Or continue using keyword-based search which is fully functional.
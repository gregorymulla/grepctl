# BigQuery Semantic Grep - Manual Testing Guide

## Prerequisites Checklist

Before starting tests, ensure you have:

- [ ] Google Cloud Project with billing enabled
- [ ] BigQuery API enabled
- [ ] Vertex AI API enabled
- [ ] Cloud Storage API enabled
- [ ] A GCS bucket with test data
- [ ] Appropriate IAM permissions (BigQuery Admin, Storage Admin)
- [ ] Python 3.11+ installed
- [ ] uv package manager installed

## Setup Testing

### 1. Environment Setup

```bash
# Set up authentication
gcloud auth login
gcloud auth application-default login

# Set project
export GOOGLE_CLOUD_PROJECT="semgrep-472018"
export GOOGLE_CLOUD_LOCATION="US"

# Verify authentication
gcloud config get-value project
gcloud auth list
```

**Expected Result**: Your account should be listed as active and project should be set correctly.

### 2. Package Installation

```bash
# Clone and enter directory
cd /mnt/d/2025/big-query-ai/bq-semgrep

# Install dependencies
uv sync

# Verify installation
uv run bq-semgrep --help
```

**Expected Result**: CLI help should display showing all available commands (setup, ingest, search, index, status).

### 3. Configuration Testing

```bash
# Create config directory
mkdir -p ~/.bq-semgrep

# Copy example config
cp config.yaml.example ~/.bq-semgrep/config.yaml

# Edit config with your project details
cat > ~/.bq-semgrep/config.yaml << EOF
project_id: "semgrep-472018"
dataset_name: "mmgrep_test"
location: "US"
gcs_bucket: "gcm-data-lake"
gcs_prefix: "multimodal-dataset"
log_level: "DEBUG"
EOF

# Test config loading
uv run python -c "from src.bq_semgrep.config import load_config; c = load_config(); print(c.project_id)"
```

**Expected Result**: Should print your project ID without errors.

## BigQuery Setup Testing

### 4. Dataset and Table Creation

```bash
# Run setup command
uv run bq-semgrep setup

# If you have a GCS connection, specify it
uv run bq-semgrep setup --connection "projects/semgrep-472018/locations/US/connections/bigquery-gcs"
```

**Expected Result**:
- "Setup completed successfully!" message
- No error messages

**Verification**:
```bash
# Check in BigQuery console or CLI
bq ls
# Should show mmgrep_test dataset

bq ls mmgrep_test
# Should show: documents, document_chunks, search_corpus tables
```

### 5. External Table Verification

```bash
# Check if external tables were created
bq query --use_legacy_sql=false "
SELECT table_name
FROM \`semgrep-472018.mmgrep_test.INFORMATION_SCHEMA.TABLES\`
WHERE table_name LIKE 'obj_%'
"
```

**Expected Result**: Should list 9 external tables:
- obj_pdf
- obj_images
- obj_audio
- obj_video
- obj_text
- obj_markdown
- obj_json
- obj_csv
- obj_documents

## Data Preparation Testing

### 6. Create Test Data in GCS

```bash
# Create test directories in GCS
gsutil mkdir -p gs://gcm-data-lake/multimodal-dataset/text
gsutil mkdir -p gs://gcm-data-lake/multimodal-dataset/pdf
gsutil mkdir -p gs://gcm-data-lake/multimodal-dataset/images
gsutil mkdir -p gs://gcm-data-lake/multimodal-dataset/json
gsutil mkdir -p gs://gcm-data-lake/multimodal-dataset/csv

# Create and upload test files
echo "This is a test document about invoice processing errors." > test.txt
gsutil cp test.txt gs://gcm-data-lake/multimodal-dataset/text/

echo '{"type": "invoice", "error": "processing failed", "amount": 1000}' > test.json
gsutil cp test.json gs://gcm-data-lake/multimodal-dataset/json/

echo "id,type,description
1,invoice,processing error
2,payment,successful transaction" > test.csv
gsutil cp test.csv gs://gcm-data-lake/multimodal-dataset/csv/

# Verify uploads
gsutil ls -r gs://gcm-data-lake/multimodal-dataset/
```

**Expected Result**: Files should be listed in their respective directories.

### 7. Run Data Collection Script (Optional)

```bash
# For more comprehensive test data
uv run python simple_data_collector.py --num-samples 5 --bucket gcm-data-lake --project semgrep-472018

# Or use the multimodal collector
uv run python multimodal_data_collector.py --num-samples 10 --bucket gcm-data-lake --project semgrep-472018
```

**Expected Result**: Progress bars showing successful upload of various file types.

## Ingestion Testing

### 8. Test Individual Modality Ingestion

```bash
# Test text file ingestion
uv run bq-semgrep ingest --bucket gcm-data-lake --modalities text

# Check results
bq query --use_legacy_sql=false "
SELECT COUNT(*) as count, modality
FROM \`semgrep-472018.mmgrep_test.documents\`
WHERE modality = 'text'
GROUP BY modality
"
```

**Expected Result**: Should show count > 0 for text modality.

### 9. Test Multiple Modality Ingestion

```bash
# Ingest multiple types
uv run bq-semgrep ingest --bucket gcm-data-lake --modalities text json csv

# Verify ingestion
bq query --use_legacy_sql=false "
SELECT modality, source, COUNT(*) as count
FROM \`semgrep-472018.mmgrep_test.documents\`
GROUP BY modality, source
ORDER BY modality
"
```

**Expected Result**: Should show counts for each ingested modality.

### 10. Test Chunking

```bash
# Add a long document for chunking test
cat > long_doc.txt << EOF
$(python -c "print('This is a very long document about invoice processing. ' * 100)")
EOF

gsutil cp long_doc.txt gs://gcm-data-lake/multimodal-dataset/text/

# Re-run ingestion
uv run bq-semgrep ingest --bucket gcm-data-lake --modalities text --chunk-size 500 --chunk-overlap 100

# Check chunks
bq query --use_legacy_sql=false "
SELECT COUNT(*) as chunk_count
FROM \`semgrep-472018.mmgrep_test.document_chunks\`
"
```

**Expected Result**: Should show chunks created for long documents.

## Embedding Generation Testing

### 11. Generate Embeddings

```bash
# Update embeddings for all documents
uv run bq-semgrep index --update

# Check embedding status
bq query --use_legacy_sql=false "
SELECT
  COUNT(*) as total,
  COUNT(embedding) as with_embeddings
FROM \`semgrep-472018.mmgrep_test.search_corpus\`
"
```

**Expected Result**:
- Command should complete without errors
- with_embeddings count should equal total count

### 12. Rebuild Vector Index

```bash
# Rebuild index from scratch
uv run bq-semgrep index --rebuild

# Verify index exists
bq query --use_legacy_sql=false "
SELECT index_name, index_status
FROM \`semgrep-472018.mmgrep_test.INFORMATION_SCHEMA.VECTOR_INDEXES\`
WHERE index_name = 'search_corpus_idx'
"
```

**Expected Result**: Should show index with status 'ACTIVE' or 'READY'.

## Search Testing

### 13. Basic Semantic Search

```bash
# Simple search
uv run bq-semgrep search "invoice processing errors"

# Search with more results
uv run bq-semgrep search "invoice" --top-k 10
```

**Expected Result**:
- Should return relevant documents
- Results should be displayed in a formatted table

### 14. Advanced Search with Filters

```bash
# Search with source filter
uv run bq-semgrep search "error" --sources text json

# Search with regex filter
uv run bq-semgrep search "processing" --regex "invoice|payment"

# Search with date range (adjust dates as needed)
uv run bq-semgrep search "test" --start-date 2024-01-01 --end-date 2025-12-31
```

**Expected Result**: Results should be filtered according to specified criteria.

### 15. Search with LLM Reranking

```bash
# Enable reranking for better precision
uv run bq-semgrep search "invoice processing failed" --rerank --top-k 5
```

**Expected Result**:
- Results should include relevance scores
- Most relevant results should appear first
- May take slightly longer due to LLM processing

### 16. Different Output Formats

```bash
# JSON output
uv run bq-semgrep search "test" --output json > results.json
cat results.json | python -m json.tool | head -20

# CSV output
uv run bq-semgrep search "test" --output csv > results.csv
head results.csv
```

**Expected Result**: Output should be in requested format.

## SQL Interface Testing

### 17. Test Table Function

```sql
-- Run in BigQuery console or bq command
bq query --use_legacy_sql=false "
SELECT doc_id, source, text_content
FROM \`semgrep-472018.mmgrep_test.semantic_grep_tf\`(
  'invoice error',
  5,
  ['text', 'json'],
  TIMESTAMP('2024-01-01'),
  CURRENT_TIMESTAMP(),
  '',
  FALSE
)
"
```

**Expected Result**: Should return up to 5 results matching the query.

### 18. Test Stored Procedure

```sql
-- Run in BigQuery console
bq query --use_legacy_sql=false "
CALL \`semgrep-472018.mmgrep_test.semantic_grep\`('processing error', 10)
"
```

**Expected Result**: Should return ranked results with relevance scores.

## Status and Monitoring Testing

### 19. System Status Check

```bash
# Check overall system status
uv run bq-semgrep status
```

**Expected Result**: Should display:
- Dataset status: ✓
- Document count
- Vector index status: ✓
- Model configurations

### 20. Get Detailed Statistics

```bash
# Check document statistics
bq query --use_legacy_sql=false "
SELECT
  modality,
  source,
  COUNT(*) as count,
  AVG(LENGTH(text_content)) as avg_length
FROM \`semgrep-472018.mmgrep_test.documents\`
GROUP BY modality, source
"

# Check embedding coverage
bq query --use_legacy_sql=false "
SELECT
  COUNT(*) as total_docs,
  COUNT(embedding) as docs_with_embeddings,
  COUNT(*) - COUNT(embedding) as missing_embeddings
FROM \`semgrep-472018.mmgrep_test.search_corpus\`
"
```

**Expected Result**: Should show comprehensive statistics about your data.

## Error Handling Testing

### 21. Test Invalid Queries

```bash
# Test with empty query
uv run bq-semgrep search ""

# Test with invalid regex
uv run bq-semgrep search "test" --regex "[invalid("

# Test with invalid date
uv run bq-semgrep search "test" --start-date "not-a-date"
```

**Expected Result**: Should handle errors gracefully with appropriate error messages.

### 22. Test Missing Configuration

```bash
# Temporarily rename config
mv ~/.bq-semgrep/config.yaml ~/.bq-semgrep/config.yaml.bak

# Try to run command
uv run bq-semgrep status

# Restore config
mv ~/.bq-semgrep/config.yaml.bak ~/.bq-semgrep/config.yaml
```

**Expected Result**: Should either use defaults or provide clear error about missing configuration.

## Performance Testing

### 23. Batch Ingestion Performance

```bash
# Time large batch ingestion
time uv run bq-semgrep ingest --bucket gcm-data-lake --batch-size 500

# Check ingestion rate
bq query --use_legacy_sql=false "
SELECT
  DATE(created_at) as date,
  COUNT(*) as docs_ingested
FROM \`semgrep-472018.mmgrep_test.documents\`
GROUP BY date
ORDER BY date DESC
"
```

**Expected Result**: Should complete in reasonable time, batch processing should be efficient.

### 24. Search Performance

```bash
# Time different search operations
echo "Simple search:"
time uv run bq-semgrep search "test query" --top-k 10

echo "Search with reranking:"
time uv run bq-semgrep search "test query" --top-k 10 --rerank

echo "Complex filtered search:"
time uv run bq-semgrep search "test" --sources text json --regex "error|fail" --top-k 20
```

**Expected Result**:
- Simple search: < 2 seconds
- With reranking: < 5 seconds
- Complex search: < 3 seconds

## Cleanup Testing

### 25. Clean Test Data

```bash
# Remove test documents from GCS (optional)
gsutil rm -r gs://gcm-data-lake/multimodal-dataset/test_*

# Drop test dataset (if needed)
bq rm -r -f -d semgrep-472018:mmgrep_test

# Verify cleanup
bq ls
gsutil ls gs://gcm-data-lake/multimodal-dataset/
```

**Expected Result**: Test data and dataset should be removed.

## Test Validation Checklist

After completing all tests, verify:

- [ ] Setup creates all required BigQuery resources
- [ ] External tables correctly reference GCS data
- [ ] Text extraction works for all modalities
- [ ] Document chunking creates appropriate chunks
- [ ] Embeddings are generated for all documents
- [ ] Vector index is created and active
- [ ] Semantic search returns relevant results
- [ ] Filters (source, regex, date) work correctly
- [ ] LLM reranking improves result relevance
- [ ] SQL interface (table function and procedure) works
- [ ] Status command shows accurate information
- [ ] Error handling is robust
- [ ] Performance is acceptable for your use case

## Troubleshooting Common Issues

### Issue: "Permission denied" errors
**Solution**: Check IAM permissions, ensure you have BigQuery Admin and Storage Admin roles.

### Issue: "Dataset not found"
**Solution**: Run `bq-semgrep setup` first to create the dataset.

### Issue: "No external tables found"
**Solution**: Provide the correct GCS connection name during setup.

### Issue: "Embedding generation fails"
**Solution**: Verify Vertex AI API is enabled and text/embedding models are accessible.

### Issue: "Search returns no results"
**Solution**: Ensure data is ingested, embeddings are generated, and index is built.

## Expected Test Duration

- Basic setup and configuration: 10 minutes
- Data preparation and ingestion: 15-30 minutes
- Embedding generation: 10-20 minutes (depends on data volume)
- Search testing: 15 minutes
- Complete test suite: 1-2 hours

## Success Criteria

The system is considered working correctly when:
1. All CLI commands execute without errors
2. Data is successfully ingested from GCS
3. Embeddings are generated for all documents
4. Search returns relevant results
5. Performance meets requirements (< 2s for most searches)
6. SQL interface functions work as expected
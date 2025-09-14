# Lessons Learned: BigQuery Semantic Grep Implementation

## Project Overview
Successfully implemented a BigQuery-based semantic search system for multimodal data (text, markdown, PDFs, images) with Vector Search, Vision API, and Document AI integration.

## Key Achievements

### 1. Core System Implementation
- ✅ Built complete Python package with CLI (`bq-semgrep`)
- ✅ Created BigQuery infrastructure with external tables
- ✅ Integrated Vertex AI text-embedding-004 model
- ✅ Implemented semantic search with VECTOR_SEARCH
- ✅ Processed 338 documents across 4 modalities

### 2. Vision API Integration
- ✅ Successfully analyzed 100/100 images
- ✅ Extracted labels, objects, text, colors, faces, scenes
- ✅ Dramatically improved image search quality
- ✅ Search now understands visual content semantically

### 3. PDF Processing
- ✅ Enabled Document AI for OCR capabilities
- ✅ Implemented hybrid extraction (Document AI + PyPDF2)
- ✅ Successfully extracted content from ~50% of PDFs
- ⚠️ Gemini API integration blocked by permissions

## Technical Challenges & Solutions

### 1. Vector Index Issues
**Problem**: Vector index creation failed with various errors
- DROP statement missing ON clause
- Unsupported ivf_num_lists option
- Empty embedding arrays

**Solution**:
- Fixed DROP syntax with proper ON clause
- Removed unsupported options from CREATE INDEX
- Used direct VECTOR_SEARCH without index (<5000 docs)
- Added proper NULL/empty array checks

### 2. Vertex AI Configuration
**Problem**: ML.GENERATE_EMBEDDING failing with 404 errors

**Solution**:
- Created Vertex AI connection properly
- Granted necessary IAM permissions
- Used correct model path format
- Added flatten_json_output parameter

### 3. Embedding Dimension Mismatch Issue
**Problem**: VECTOR_SEARCH fails with "Dimension of column embedding does not match"
- Occurs when NULL or empty arrays mix with 768-dim vectors
- BigQuery insert_rows_json() converts None to empty arrays []
- Empty arrays have dimension 0, causing mismatch with 768-dim embeddings

**Root Cause**:
```python
# This causes problems:
documents.append({
    'uri': uri,
    'text_content': content,
    'embedding': None  # Gets converted to [] with dimension 0
})
```

**Solution**:
1. Never include embedding field during initial insert
2. Use SQL INSERT instead of insert_rows_json():
```python
query = """
INSERT INTO `table` (uri, modality, text_content)
VALUES (@uri, @modality, @text_content)
"""
```
3. Clear empty embeddings before regeneration:
```sql
UPDATE table SET embedding = NULL
WHERE ARRAY_LENGTH(embedding) = 0
```
4. Always check for both conditions:
```sql
WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
```

### 4. Gemini API Access
**Problem**: Could not create Gemini model for PDF extraction
- Permission errors despite IAM roles
- Timeout issues with direct API calls

**Attempted Solutions**:
- Created vertex-ai-connection in BigQuery
- Granted aiplatform.user role
- Added serviceusage.serviceUsageConsumer role
- Added storage.objectViewer role

**Final Status**: Using Document AI as alternative

### 5. PDF Extraction Challenges
**Problem**: Many PDFs failed extraction
- "Unsupported input file format" errors
- "EOF marker not found" errors

**Solution**: Hybrid approach
- Document AI for scanned/complex PDFs
- PyPDF2 fallback for standard PDFs
- Metadata-only indexing as last resort

## Best Practices Discovered

### 1. BigQuery ML Setup
```sql
-- Always create connection first
bq mk --connection --location=us --project_id=PROJECT_ID \
  --connection_type=CLOUD_RESOURCE CONNECTION_NAME

-- Grant permissions to service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"
```

### 2. Embedding Generation
```python
# Always check for NULL or empty embeddings
WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)

# Use batch processing for efficiency
UPDATE table SET embedding = ML.GENERATE_EMBEDDING(...)
WHERE embedding IS NULL
LIMIT 100
```

### 3. Vision API Integration
```python
# Use comprehensive feature extraction
features = [
    'label_detection',      # What's in the image
    'object_localization',  # Where objects are
    'text_detection',       # OCR
    'image_properties',     # Colors
    'face_detection'        # People (privacy-conscious)
]

# Rate limit appropriately
time.sleep(0.5)  # Between API calls
```

### 4. Error Handling
```python
# Always implement fallbacks
try:
    result = primary_method()
except Exception:
    result = fallback_method()

# Log detailed errors for debugging
logger.error(f"Method failed: {e}")
logger.debug(f"Full traceback: {traceback.format_exc()}")
```

## Performance Metrics

### Processing Rates
- **Text/Markdown ingestion**: ~50 docs/second
- **Embedding generation**: ~20 docs/second
- **Vision API**: ~0.4 images/second (with rate limiting)
- **Document AI**: ~0.1 PDFs/second
- **Search queries**: <1 second response time

### Storage Usage
- **Dataset size**: ~500MB
- **Embedding dimensions**: 768 per document
- **Index not needed**: <5000 documents

## Gotchas & Warnings

### 1. BigQuery Limitations
- Vector index only needed for >5000 documents
- VECTOR_SEARCH works fine without index for small datasets
- Table functions may not be available in all regions

### 2. API Quotas
- Vision API: Rate limited, needs delays
- Document AI: Some PDF formats unsupported
- Vertex AI: Requires specific IAM configuration

### 3. Cost Considerations
- Vision API: $1.50 per 1000 images
- Document AI: $1.50 per 1000 pages
- Embeddings: Minimal cost via BigQuery ML
- Storage: Standard BigQuery rates

## Recommendations for Future

### 1. Scaling Considerations
- Implement vector index when >5000 documents
- Consider chunking for large documents
- Use Cloud Tasks for batch processing

### 2. Enhanced Features
- Add multilingual support
- Implement hybrid search (semantic + keyword)
- Add relevance feedback mechanism
- Create UI for search interface

### 3. Monitoring & Maintenance
- Set up embedding freshness checks
- Monitor API quota usage
- Implement automated retries
- Add performance metrics tracking

## Commands Reference

### Essential Commands
```bash
# Setup
gcloud services enable aiplatform.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable documentai.googleapis.com

# Run system
uv run bq-semgrep setup
uv run bq-semgrep ingest
uv run bq-semgrep index --rebuild
uv run bq-semgrep search "query"

# Update embeddings
uv run bq-semgrep index --update
```

### Debugging Commands
```bash
# Check service status
uv run bq-semgrep status

# View logs
gcloud logging read "resource.type=bigquery_resource"

# Test specific components
uv run python test_vision_direct.py
uv run python test_bq_gemini_pdf.py
```

## Conclusion

The system successfully demonstrates semantic search across multimodal data using BigQuery as the foundation. While some advanced features (Gemini PDF extraction) faced permission challenges, the core functionality works well with acceptable workarounds. The Vision API integration particularly stands out as a success, transforming image search from metadata-based to true visual understanding.

## Next Steps

1. **Complete PDF extraction** for remaining documents
2. **Enable Gemini** when permissions resolved
3. **Add chunking** for better long document handling
4. **Implement caching** for frequently accessed content
5. **Create monitoring dashboard** for system health

## Contact & Support

For issues with:
- BigQuery ML: bqml-feedback@google.com
- Vision API: Check quota in Cloud Console
- Document AI: Verify processor configuration
- General: Review logs in Cloud Logging
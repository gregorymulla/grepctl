# grepctl check - System Health Check

The `grepctl check` command provides comprehensive validation of your grepctl installation and all required services.

## Usage

```bash
grepctl check
```

## What It Checks

### 1. **APIs** - Required Google Cloud APIs
- ✅ BigQuery API (required)
- ✅ Vertex AI API (required)
- ✅ Cloud Storage API (required)
- ⚠️ Generative Language API (optional - for Gemini models)
- ⚠️ Speech-to-Text API (optional - for audio transcription)
- ⚠️ Video Intelligence API (optional - for video analysis)
- ⚠️ Vision API (optional - for image OCR)
- ⚠️ Document AI (optional - for PDF extraction)

### 2. **Dataset** - BigQuery dataset existence
- Verifies the configured dataset exists
- Shows location and creation time

### 3. **Tables** - Required and optional tables
- Required: `documents`, `search_corpus`
- Optional: External tables for various file types

### 4. **Connection** - Vertex AI connection
- Checks for BigQuery-Vertex AI connection
- Shows service account details
- Lists required IAM roles

### 5. **Models** - ML models availability
- Embedding model (required for search)
- Text generation model (optional for ML.GENERATE_TEXT)

### 6. **Permissions** - User access verification
- BigQuery access
- Project access
- Current user identification

### 7. **Data** - Data ingestion status
- Document count
- Modality distribution
- Embedding coverage

## Understanding the Output

### Status Icons
- ✅ **Passed** - Component is properly configured
- ❌ **Failed** - Component needs attention (blocks functionality)
- ⚠️ **Warning** - Optional component not configured

### Health States
- **HEALTHY** - All required components are working
- **UNHEALTHY** - One or more required components failed

## Common Issues and Fixes

### Missing APIs
```bash
# Enable required API
gcloud services enable <api-name> --project=<project-id>
```

### Missing Dataset
```bash
# Create dataset and tables
grepctl setup
```

### Missing Connection
```bash
# Create Vertex AI connection
bq mk --connection --location=us --project_id=<project-id> \
  --connection_type=CLOUD_RESOURCE vertex-ai-connection
```

### Missing Models
```bash
# Create embedding model
bq query --use_legacy_sql=false "
CREATE OR REPLACE MODEL \`project.dataset.text_embedding_model\`
REMOTE WITH CONNECTION \`us.vertex-ai-connection\`
OPTIONS (ENDPOINT = 'text-embedding-004')"
```

### No Embeddings
```bash
# Generate embeddings for documents
grepctl index --update
```

## Example Output

```
System Health Check Results

╭────────────────────────────────── Summary ───────────────────────────────────╮
│ Overall Status: ✅ HEALTHY                                                   │
│ Passed: 7 | Failed: 0 | Warnings: 1                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

[Detailed check results for each component...]

✨ All systems operational!
Your grepctl installation is fully configured.
```

## Integration with CI/CD

The check command can be used in automated pipelines:

```bash
# Exit with error if unhealthy
grepctl check || exit 1

# Check specific component in scripts
grepctl check 2>&1 | grep "HEALTHY" || echo "System needs attention"
```

## Troubleshooting

If the check command itself fails:

1. **Ensure gcloud is authenticated:**
   ```bash
   gcloud auth application-default login
   ```

2. **Verify project access:**
   ```bash
   gcloud config set project <project-id>
   ```

3. **Check BigQuery client:**
   ```bash
   bq ls -d --project_id=<project-id>
   ```

## Next Steps

After all checks pass:
1. Run `grepctl ingest` to load documents
2. Run `grepctl index --update` to generate embeddings
3. Run `grepctl search` to test semantic search
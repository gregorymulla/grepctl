# grepctl - BigQuery Semantic Grep Controller

A comprehensive CLI utility for managing all aspects of the BigQuery Semantic Grep (mmgrep) system, from initial setup to multimodal search.

## Quick Start

### One-Command Setup and Ingestion

```bash
# Complete setup with automatic ingestion of all modalities
uv run python grepctl.py init all --bucket gcm-data-lake --auto-ingest
```

This single command will:
1. Enable all required Google Cloud APIs
2. Create BigQuery dataset and tables
3. Set up ML models for embeddings
4. Ingest all modalities from your GCS bucket
5. Generate embeddings for semantic search

## Installation

```bash
# Ensure dependencies are installed
uv sync

# Make grepctl executable (optional)
chmod +x grepctl.py
```

## Commands Overview

### Initialize System (`init`)

```bash
# Complete setup with auto-ingestion
grepctl init all --bucket your-bucket --auto-ingest

# Setup dataset and tables only
grepctl init dataset

# Create ML models
grepctl init models

# Generate/update configuration
grepctl init config --project your-project --dataset mmgrep
```

### Manage APIs (`apis`)

```bash
# Enable all required APIs
grepctl apis enable --all

# Enable specific API
grepctl apis enable --api vision.googleapis.com

# Check API status
grepctl apis check
```

### Ingest Data (`ingest`)

```bash
# Process all modalities
grepctl ingest all

# Process specific modalities
grepctl ingest pdf
grepctl ingest images
grepctl ingest audio
grepctl ingest video
grepctl ingest json
```

### Manage Embeddings (`index`)

```bash
# Rebuild all embeddings
grepctl index rebuild

# Update missing embeddings
grepctl index update

# Verify embedding health
grepctl index verify
```

### Fix Issues (`fix`)

```bash
# Fix embedding dimension issues
grepctl fix embeddings

# Handle stuck processing
grepctl fix stuck --modality pdf

# Validate data integrity
grepctl fix validate
```

### Check Status

```bash
# Display comprehensive system status
grepctl status
```

### Search Data

```bash
# Basic search
grepctl search "your query"

# Advanced search with filters
grepctl search "machine learning" -k 20 -m pdf -m markdown

# Output in different formats
grepctl search "data analysis" -o json
grepctl search "python code" -o csv
```

## Configuration

grepctl uses a YAML configuration file located at `~/.grepctl.yaml`:

```yaml
project_id: semgrep-472018
dataset: mmgrep
bucket: gcm-data-lake
location: US
vertex_connection: vertex-ai-connection
batch_size: 100
chunk_size: 1000
chunk_overlap: 200
```

You can override the config file location:
```bash
grepctl --config /path/to/config.yaml status
```

## Workflow Examples

### Starting Fresh

```bash
# 1. Enable APIs
grepctl apis enable --all

# 2. Initialize dataset
grepctl init dataset

# 3. Ingest all data
grepctl ingest all

# 4. Generate embeddings
grepctl index update

# 5. Verify system
grepctl status

# 6. Search!
grepctl search "your query"
```

### Fixing Issues

```bash
# Check what's wrong
grepctl status
grepctl index verify

# Fix embedding issues
grepctl fix embeddings

# Retry stuck modalities
grepctl fix stuck --modality pdf
grepctl ingest pdf

# Regenerate embeddings
grepctl index update
```

### Adding New Data

```bash
# After adding files to GCS bucket
grepctl ingest all --resume
grepctl index update
```

## Modality Support

grepctl handles 8 different modalities:

| Modality | Extensions | Processing Method |
|----------|------------|-------------------|
| Text | .txt, .log | Direct text extraction |
| Markdown | .md, .markdown | Markdown parsing |
| PDF | .pdf | Document AI + PyPDF2 |
| Images | .jpg, .png, etc | Vision API analysis |
| Audio | .mp3, .wav, etc | Speech-to-Text |
| Video | .mp4, .avi, etc | Video Intelligence |
| JSON | .json, .jsonl | Structured data parsing |
| CSV | .csv, .tsv | Tabular data analysis |

## Troubleshooting

### Embedding Dimension Errors

```bash
# This fixes empty arrays and dimension mismatches
grepctl fix embeddings
```

### API Not Enabled

```bash
# Enable all required APIs
grepctl apis enable --all

# Check which APIs are enabled
grepctl apis check
```

### Processing Stuck

```bash
# Clear stuck embeddings and retry
grepctl fix stuck
grepctl index update
```

### PDF Extraction Failed

```bash
# Re-run PDF extraction with hybrid approach
grepctl ingest pdf
```

## Advanced Usage

### Parallel Processing

Process multiple modalities in parallel:

```bash
# Run these in separate terminals
grepctl ingest pdf &
grepctl ingest images &
grepctl ingest audio &
```

### Custom Configuration

Create a custom config for different projects:

```bash
# Create project-specific config
cat > project1.yaml << EOF
project_id: project1
dataset: search_data
bucket: project1-bucket
EOF

# Use custom config
grepctl --config project1.yaml init all
```

### Batch Operations

```bash
# Process specific bucket prefix
export BUCKET_PREFIX="2024/documents"
grepctl ingest all

# Generate embeddings in batches
grepctl index update
```

## Environment Variables

- `GOOGLE_CLOUD_PROJECT` - Default GCP project
- `GOOGLE_APPLICATION_CREDENTIALS` - Service account credentials

## Requirements

- Python 3.11+
- uv package manager
- Google Cloud SDK (gcloud)
- Required APIs enabled:
  - BigQuery
  - Vertex AI
  - Vision API
  - Document AI
  - Speech-to-Text
  - Video Intelligence
  - Cloud Storage

## Related Tools

grepctl integrates with:
- `grepctl` - Core search functionality
- `fix_embeddings.py` - Embedding repair utility
- `show_status.py` - Status display
- Various ingestion scripts for each modality

## Support

For issues or questions:
1. Check status: `grepctl status`
2. Verify APIs: `grepctl apis check`
3. Fix embeddings: `grepctl fix embeddings`
4. Review logs in `~/.grepctl/logs/`
# BigQuery Semantic Grep - Usage Guide

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Setup](#setup)
4. [Data Ingestion](#data-ingestion)
5. [Searching](#searching)
6. [Management](#management)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/grepctl.git
cd grepctl

# Install with uv
uv sync

# Or install with pip
pip install -e .
```

## Configuration

### Environment Variables

Set these environment variables for authentication:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Configuration File

Create a configuration file at `~/.grepctl/config.yaml`:

```yaml
project_id: "your-project-id"
dataset_name: "mmgrep"
location: "US"
gcs_bucket: "gcm-data-lake"
gcs_prefix: "multimodal-dataset"
```

## Setup

### 1. Create BigQuery Dataset and Tables

```bash
# Create dataset, tables, and functions
grepctl setup --connection "your-gcs-connection"

# Check setup status
grepctl status
```

### 2. Create External Tables for GCS Access

The setup command automatically creates external tables for each modality:
- `obj_pdf` - PDF documents
- `obj_images` - Image files
- `obj_audio` - Audio recordings
- `obj_video` - Video files
- `obj_text` - Plain text files
- `obj_markdown` - Markdown documents
- `obj_json` - JSON data
- `obj_csv` - CSV tables
- `obj_documents` - Office documents

## Data Ingestion

### Ingest All Modalities

```bash
# Ingest all data types from GCS
grepctl ingest --bucket gcm-data-lake --dataset mmgrep

# Ingest specific modalities only
grepctl ingest --bucket gcm-data-lake -m pdf -m images -m audio
```

### Ingestion Options

```bash
# Custom chunking parameters
grepctl ingest \
    --bucket gcm-data-lake \
    --chunk-size 1000 \
    --chunk-overlap 200 \
    --batch-size 100
```

## Searching

### Basic Search

```bash
# Simple semantic search
grepctl search "invoice processing errors"

# Get more results
grepctl search "customer churn analysis" --top-k 50
```

### Advanced Search

```bash
# Filter by source types
grepctl search "onboarding issues" \
    --sources pdf screenshot recording \
    --top-k 20

# Add regex filter
grepctl search "energy crisis" \
    --regex "blackout|outage|load.?shedding" \
    --sources pdf

# Date range filter
grepctl search "quarterly report" \
    --start-date 2024-01-01 \
    --end-date 2024-12-31

# Enable LLM reranking for better precision
grepctl search "technical documentation API" \
    --rerank \
    --top-k 10
```

### Output Formats

```bash
# Default table output
grepctl search "query" --output table

# JSON output for processing
grepctl search "query" --output json > results.json

# CSV output for analysis
grepctl search "query" --output csv > results.csv
```

## Management

### Vector Index Management

```bash
# Rebuild vector index from scratch
grepctl index --rebuild

# Update embeddings for new documents
grepctl index --update
```

### System Status

```bash
# Check system status
grepctl status
```

Output shows:
- Dataset status
- Document count
- Vector index status
- Model configuration

## SQL Access

You can also query directly using SQL:

### Using Table Function

```sql
SELECT * FROM `your-project.mmgrep.semantic_grep_tf`(
    'onboarding invoice errors',     -- query
    20,                               -- top_k
    ['pdf', 'screenshot'],            -- source_filter
    TIMESTAMP('2024-01-01'),          -- start_ts
    CURRENT_TIMESTAMP(),              -- end_ts
    r'(?i)invoice|error',             -- regex
    TRUE                              -- use_rerank
);
```

### Using Stored Procedure

```sql
CALL `your-project.mmgrep.semantic_grep`(
    'first signs of confusion after onboarding',
    25
);
```

## Modality-Specific Processing

### PDF Files
- Automatic text extraction
- Structure preservation
- Metadata extraction

### Images
- OCR for text extraction
- Visual content summarization
- Screenshot text capture

### Audio/Video
- Automatic transcription
- Speaker identification (when possible)
- Timestamp extraction

### Structured Data (JSON/CSV)
- Natural language summarization
- Key field extraction
- Statistical information

## Performance Tips

1. **Chunking**: Optimal chunk size is 1000-1500 characters with 200-300 overlap
2. **Batch Size**: Use 100-500 for ingestion batches
3. **Reranking**: Only rerank top 50-100 candidates for best performance
4. **Index Rebuild**: Rebuild weekly or after large ingestion batches

## Troubleshooting

### Common Issues

1. **Authentication Error**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```

2. **Dataset Not Found**
   ```bash
   grepctl setup
   ```

3. **No External Tables**
   ```bash
   grepctl setup --connection "your-gcs-connection"
   ```

4. **Slow Search**
   - Rebuild vector index: `grepctl index --rebuild`
   - Reduce rerank candidates
   - Use source filters to narrow search

## Example Workflows

### Complete Setup and Ingestion

```bash
# 1. Setup BigQuery resources
grepctl setup

# 2. Ingest all data
grepctl ingest --bucket gcm-data-lake

# 3. Build vector index
grepctl index --rebuild

# 4. Test search
grepctl search "test query"
```

### Daily Update Workflow

```bash
# 1. Ingest new data
grepctl ingest --bucket gcm-data-lake

# 2. Update embeddings
grepctl index --update

# 3. Check status
grepctl status
```

## API Usage

```python
from grepctl.config import Config
from grepctl.bigquery.connection import BigQueryClient
from grepctl.search.vector_search import SemanticSearch

# Initialize
config = Config()
client = BigQueryClient(config)
searcher = SemanticSearch(client, config)

# Search
results = searcher.search(
    query="your search query",
    top_k=20,
    source_filter=['pdf', 'screenshot'],
    use_rerank=True
)

# Process results
for result in results:
    print(f"Score: {result['rel_score']:.3f}")
    print(f"Content: {result['text_content'][:200]}...")
```
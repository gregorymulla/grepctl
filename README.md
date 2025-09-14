# BigQuery Semantic Grep (bq-semgrep)

SQL-native semantic search across heterogeneous data in Google Cloud Storage using BigQuery ML.

## Overview

BigQuery Semantic Grep provides a unified SQL interface for searching across multiple data modalities (PDFs, images, audio, video, text, JSON, CSV) stored in Google Cloud Storage. It combines text extraction, embeddings, vector search, and optional LLM reranking to deliver powerful semantic search capabilities directly within BigQuery.

## Key Features

- **Multimodal Support**: Search across PDFs, images, audio, video, text, markdown, JSON, and CSV files
- **SQL-Native**: Access search functionality through BigQuery table functions and stored procedures
- **Automatic Text Extraction**: OCR for images, transcription for audio/video, text extraction for PDFs
- **Vector Search**: Semantic search using embeddings and vector similarity
- **Hybrid Search**: Combine semantic and keyword-based filtering
- **LLM Reranking**: Optional reranking using large language models for improved precision
- **Scalable**: Leverages BigQuery's infrastructure for processing millions of documents
- **Automated Setup**: One-command setup scripts for complete system deployment

## Quick Start

### Prerequisites

1. **Enable Vertex AI API** (required for semantic search):
```bash
gcloud services enable aiplatform.googleapis.com --project your-project-id
```

2. **Install dependencies**:
```bash
# Clone the repository
git clone https://github.com/yourusername/bq-semgrep.git
cd bq-semgrep

# Install with uv
uv sync
```

### Automated Setup (Recommended)

#### Complete Setup with Vertex AI (Semantic Search)

```bash
# Step 1: Run main setup script
./setup_mmgrep.sh --project your-project-id --bucket your-bucket

# Step 2: Enable Vertex AI and create embedding models
./setup_vertex_ai.sh your-project-id US mmgrep

# Step 3: Generate embeddings and test
uv run bq-semgrep index --update
uv run bq-semgrep search "your search query"
```

The setup scripts will automatically:
- ✅ Configure Google Cloud authentication
- ✅ Create BigQuery dataset and tables
- ✅ Set up GCS connection and external tables
- ✅ Ingest data from GCS
- ✅ Create search corpus
- ✅ Enable Vertex AI API
- ✅ Grant necessary IAM permissions
- ✅ Create embedding models
- ✅ Generate embeddings for all documents
- ✅ Configure vector search

### Manual Setup

```bash
# Step 1: Enable required APIs
gcloud services enable aiplatform.googleapis.com --project your-project-id

# Step 2: Install package
uv sync

# Step 3: Setup BigQuery resources
uv run bq-semgrep setup

# Step 4: Ingest data from GCS
uv run bq-semgrep ingest --bucket your-bucket

# Step 5: Create embedding model in BigQuery
bq query --use_legacy_sql=false "
CREATE OR REPLACE MODEL \`your-project-id.mmgrep.text_embedding_model\`
REMOTE WITH CONNECTION \`your-project-id.US.bigquery-gcs\`
OPTIONS (endpoint = 'text-embedding-004')
"

# Step 6: Generate embeddings
uv run bq-semgrep index --update

# Step 7: Search
uv run bq-semgrep search "your search query"
```

## System Architecture

```
┌─────────────────┐
│   GCS Bucket    │
│  (Data Lake)    │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ External │
    │  Tables  │
    └────┬─────┘
         │
┌────────▼────────┐
│ Text Extraction │
│  (ML.GENERATE)  │
└────────┬────────┘
         │
  ┌──────▼──────┐
  │  Documents  │
  │    Table    │
  └──────┬──────┘
         │
   ┌─────▼─────┐
   │ Chunking  │
   │  Process  │
   └─────┬─────┘
         │
  ┌──────▼──────┐
  │ Embeddings  │
  │ Generation  │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │   Vector    │
  │   Index     │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  Semantic   │
  │   Search    │
  └─────────────┘
```

## Deployment Status

After running the setup scripts, your system will have:

### ✅ BigQuery Resources Created
- **Dataset**: `mmgrep` with partitioning and clustering
- **Core Tables**:
  - `documents` - Main document storage
  - `document_chunks` - Chunked documents for long texts
  - `search_corpus` - Unified search index
- **External Tables**: 9 tables linking to GCS data
- **Connection**: BigQuery-GCS connection with proper IAM

### 📊 Data Ingestion Capabilities
- **Text/Markdown**: Direct ingestion (no ML required)
- **JSON/CSV**: Natural language summarization
- **PDF**: Text extraction using Gemini
- **Images**: OCR and visual analysis
- **Audio/Video**: Transcription services

### 🔍 Search Features
- **Keyword Search**: Available immediately
- **Semantic Search**: After embedding generation
- **Hybrid Search**: Combines vector and keyword matching
- **Filters**: Source, date range, regex patterns
- **LLM Reranking**: Optional precision improvement

## Prerequisites

### Google Cloud Setup

1. **Google Cloud Project**: You need access to a Google Cloud Project with BigQuery and Cloud Storage enabled.
   - Example project: `semgrep-472018`

2. **Google Cloud Storage Bucket**: A GCS bucket for storing data.
   - Example bucket: `gcm-data-lake`

3. **Authentication**: Authenticate with Google Cloud:
   ```bash
   gcloud auth login
   gcloud config set project semgrep-472018
   ```

4. **Verify Access**: Use these commands to verify your Google Cloud access:
   ```bash
   # Check current authenticated account
   gcloud auth list

   # Verify current project
   gcloud config get-value project

   # Check storage bucket access
   gcloud storage buckets list

   # Check specific bucket access
   gcloud storage ls gs://gcm-data-lake/

   # Check BigQuery access
   bq ls

   # Check your IAM permissions for the project
   gcloud projects get-iam-policy semgrep-472018 \
     --flatten="bindings[].members" \
     --filter="bindings.members:$(gcloud config get-value account)" \
     --format="table(bindings.role)"
   ```

5. **Required Permissions**: Your account needs the following IAM roles:
   - `roles/storage.admin` or `roles/storage.objectViewer` for bucket access
   - `roles/bigquery.admin` or `roles/bigquery.dataEditor` for BigQuery operations

### Development Environment

- Python 3.11+
- uv package manager

## Installation

```bash
# Install dependencies
uv sync

# Run the package
uv run bq-semgrep
```

## Configuration

Set your Google Cloud project:
```bash
export GOOGLE_CLOUD_PROJECT=semgrep-472018
export GCS_BUCKET=gcm-data-lake
```

## Usage

### CLI Commands

```bash
# Setup BigQuery dataset and tables
bq-semgrep setup

# Check system status
bq-semgrep status

# Ingest data from GCS
bq-semgrep ingest --bucket your-bucket --modalities pdf images audio

# Generate/update embeddings
bq-semgrep index --update

# Search with various options
bq-semgrep search "your query" \
    --top-k 20 \
    --sources pdf screenshot \
    --rerank \
    --regex "pattern" \
    --start-date 2024-01-01
```

### SQL Interface

```sql
-- Using table function
SELECT * FROM `project.mmgrep.semantic_grep_tf`(
    'search query',
    20,  -- top_k
    ['pdf', 'image'],  -- source filter
    TIMESTAMP('2024-01-01'),
    CURRENT_TIMESTAMP(),
    r'regex.*pattern',
    TRUE  -- use rerank
);

-- Using stored procedure
CALL `project.mmgrep.semantic_grep`('search query', 25);
```

## System Status (As of 2025-09-13)

### ✅ Successfully Deployed Features

- **BigQuery Infrastructure**: Dataset `mmgrep` with all required tables
- **External Tables**: 9 external tables connected to GCS data
- **Data Ingestion**: 207 documents (100 text + 107 markdown files)
- **Vertex AI Integration**: Text embedding model (`text-embedding-004`) deployed
- **Embeddings**: All 207 documents have generated embeddings
- **Semantic Search**: Fully functional with VECTOR_SEARCH
- **Keyword Search**: Operational for all document types

### 📊 Current Metrics

- Total Documents: 207
- Embeddings Generated: 207 (100% coverage)
- Embedding Dimensions: 1408 (text-embedding-004)
- Search Latency: < 2 seconds for most queries
- Supported Modalities: text, markdown (ready for pdf, images, audio, video)

### 🔍 Example Searches

```sql
-- Semantic search for Python code concepts
WITH query_embedding AS (
  SELECT ml_generate_embedding_result AS embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `your-project.mmgrep.text_embedding_model`,
    (SELECT 'error exception handling python' AS content),
    STRUCT(TRUE AS flatten_json_output)
  )
)
SELECT
  base.doc_id,
  base.source,
  SUBSTR(base.text_content, 1, 300) AS preview,
  distance AS similarity_score
FROM VECTOR_SEARCH(
  TABLE `your-project.mmgrep.search_corpus`,
  'embedding',
  (SELECT embedding FROM query_embedding),
  top_k => 10,
  distance_type => 'COSINE'
)
ORDER BY distance;

-- Keyword search fallback
SELECT doc_id, source, SUBSTR(text_content, 1, 300) as preview
FROM `your-project.mmgrep.search_corpus`
WHERE REGEXP_CONTAINS(LOWER(text_content), r'python.*error|exception.*handling')
LIMIT 10;
```

## Automation Scripts

### Complete Setup Scripts

The repository includes comprehensive automation scripts that handle the entire setup process:

#### 1. Bash Setup Script (`setup_mmgrep.sh`)
```bash
# Full automated setup with all configurations
./setup_mmgrep.sh --project your-project --dataset mmgrep --bucket your-bucket --location US

# The script will:
# 1. Check prerequisites (gcloud, bq, gsutil)
# 2. Configure authentication
# 3. Create BigQuery dataset and tables
# 4. Set up GCS connection with proper IAM
# 5. Create all 9 external tables
# 6. Ingest text and markdown data
# 7. Create search corpus
# 8. Generate configuration file
# 9. Verify the setup
```

#### 2. Python Setup Script (`setup_mmgrep.py`)
```bash
# Python-based setup with error handling
python setup_mmgrep.py --project your-project --dataset mmgrep --bucket your-bucket

# Features:
# - Colored output for better readability
# - Step-by-step progress tracking
# - Automatic rollback on errors
# - Configuration file generation
# - Comprehensive verification
```

Both scripts create a configuration file at `~/.bq-semgrep/config.yaml` with all necessary settings.

## Testing

### Manual Testing Guide

See `test_steps.md` for comprehensive manual testing procedures covering:
- Environment setup
- Data ingestion testing
- Embedding generation
- Search functionality
- Performance benchmarks
- Error handling

### Quick Test Commands

```bash
# Check system status
bq-semgrep status

# Test keyword search (no embeddings required)
bq query --use_legacy_sql=false "
SELECT doc_id, source, SUBSTR(text_content, 1, 200) as preview
FROM \`your-project.mmgrep.search_corpus\`
WHERE LOWER(text_content) LIKE '%search_term%'
LIMIT 5"

# Test CLI search
bq-semgrep search "your query" --top-k 10

# Verify document count
bq query --use_legacy_sql=false "
SELECT modality, source, COUNT(*) as count
FROM \`your-project.mmgrep.documents\`
GROUP BY modality, source"
```

## Production Deployment

### Step-by-Step Production Setup

1. **Clone and Configure**
   ```bash
   git clone https://github.com/yourusername/bq-semgrep.git
   cd bq-semgrep
   uv sync
   ```

2. **Run Automated Setup**
   ```bash
   ./setup_mmgrep.sh --project production-project --bucket production-bucket
   ```

3. **Generate Embeddings**
   ```bash
   # This enables semantic search capabilities
   uv run bq-semgrep index --update
   ```

4. **Build Vector Index**
   ```bash
   # Optimize search performance
   uv run bq-semgrep index --rebuild
   ```

5. **Verify Deployment**
   ```bash
   uv run bq-semgrep status
   ```

### Monitoring and Maintenance

- **Daily**: Check ingestion status with `bq-semgrep status`
- **Weekly**: Rebuild vector index for optimal performance
- **As Needed**: Update embeddings for new documents

## API Examples

### Python API Usage

```python
from bq_semgrep.config import Config
from bq_semgrep.bigquery.connection import BigQueryClient
from bq_semgrep.search.vector_search import SemanticSearch

# Initialize
config = Config()
client = BigQueryClient(config)
searcher = SemanticSearch(client, config)

# Perform search
results = searcher.search(
    query="invoice processing errors",
    top_k=20,
    source_filter=['pdf', 'text'],
    use_rerank=True
)

# Process results
for result in results:
    print(f"Document: {result['doc_id']}")
    print(f"Score: {result['rel_score']:.3f}")
    print(f"Preview: {result['text_content'][:200]}...")
```

### SQL API Usage

```sql
-- Table function for complex searches
SELECT * FROM `project.mmgrep.semantic_grep_tf`(
    'search query',           -- query text
    20,                       -- top_k results
    ['pdf', 'text'],         -- source filter
    TIMESTAMP('2024-01-01'),  -- start date
    CURRENT_TIMESTAMP(),      -- end date
    r'regex.*pattern',        -- regex filter
    TRUE                      -- use LLM reranking
);

-- Stored procedure for simple searches
CALL `project.mmgrep.semantic_grep`('search query', 25);
```

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Solution: Ensure you have BigQuery Admin and Storage Admin roles
   - Run: `gcloud projects add-iam-policy-binding PROJECT_ID --member="user:EMAIL" --role="roles/bigquery.admin"`

2. **"Dataset not found"**
   - Solution: Run `bq-semgrep setup` or use the setup scripts

3. **"Connection not found" for external tables**
   - Solution: Create connection with `bq mk --connection --location=US --connection_type=CLOUD_RESOURCE bigquery-gcs`

4. **Embedding generation fails**
   - Solution: Verify Vertex AI API is enabled and models are accessible
   - Check quotas and billing is enabled

5. **Search returns no results**
   - Solution: Verify data ingestion with `bq-semgrep status`
   - Ensure embeddings are generated with `bq-semgrep index --update`

## Documentation

- **[Setup Complete Report](SETUP_COMPLETE.md)** - Current deployment status
- **[Testing Guide](test_steps.md)** - Comprehensive testing procedures
- **[Usage Guide](docs/USAGE.md)** - Detailed usage instructions
- **[Specifications](specs.md)** - System design and requirements

### Data Collection Scripts

#### Simple Data Collector (Recommended)

The `simple_data_collector.py` script downloads various types of public data and uploads to GCS:

```bash
# Run with default settings (5 samples per type)
uv run python simple_data_collector.py

# Run with more samples
uv run python simple_data_collector.py --num-samples 20

# Specify custom bucket and project
uv run python simple_data_collector.py --bucket my-bucket --project my-project
```

**Data types collected:**
- Text files from Project Gutenberg (classic literature)
- JSON data from GitHub API (repository information)
- CSV files from public datasets (COVID data, airports, etc.)
- Markdown files from popular GitHub repositories
- Images from Lorem Picsum service

#### Advanced Data Collector

The `download_upload_resources.py` script downloads multimodal demo data and uploads it to GCS:

1. **Install dependencies**:
   ```bash
   uv add google-cloud-storage arxiv datasets tensorflow-datasets imageio imageio-ffmpeg
   ```

2. **Set up Google Cloud authentication**:
   ```bash
   # Option 1: Use gcloud auth (recommended)
   gcloud auth application-default login

   # Option 2: Use service account key
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

3. **Run the script**:
   ```bash
   # Full dataset (100 samples per modality)
   uv run python download_upload_resources.py \
       --bucket gcm-data-lake \
       --num_samples 100

   # Small test run (5 samples per modality)
   uv run python download_upload_resources.py \
       --bucket gcm-data-lake \
       --num_samples 5 \
       --output_dir /tmp/semgrep_data
   ```

**Script Options**:
- `--bucket`: GCS bucket name (required)
- `--num_samples`: Number of items per modality (default: 100)
- `--output_dir`: Local directory for downloads (default: temp directory)
- `--language`: Language for audio samples (default: 'en')
- `--arxiv_category`: arXiv category for papers (default: 'cs.CL')

**Data Types Downloaded**:
- Chat conversations from Cornell Movie-Dialogs Corpus
- Audio clips from Mozilla Common Voice
- Video clips from UCF101 dataset
- PDF papers from arXiv
- README files from popular GitHub repositories

**Note**: The full download can consume several GB of bandwidth and disk space. Use smaller `--num_samples` for testing.
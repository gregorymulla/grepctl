# BigQuery Semantic Grep (bq-semgrep)

🚀 **One-command multimodal semantic search across your entire data lake using BigQuery ML and Google Cloud AI.**

## 🎯 Quick Start - From Zero to Search in One Command

```bash
# Complete setup with automatic data ingestion
grepctl init all --bucket your-bucket --auto-ingest

# Start searching immediately
grepctl search "find all mentions of machine learning"
```

That's it! The system automatically:
- ✅ Enables all required Google Cloud APIs
- ✅ Creates BigQuery dataset and tables
- ✅ Deploys Vertex AI embedding models
- ✅ Ingests all 8 data modalities from your GCS bucket
- ✅ Generates 768-dimensional embeddings
- ✅ Configures semantic search with VECTOR_SEARCH

## 📊 What is BigQuery Semantic Grep?

A unified SQL interface for searching across **8 different data types** stored in Google Cloud Storage:
- 📄 **Text & Markdown** - Direct content extraction
- 📑 **PDF Documents** - OCR with Document AI
- 🖼️ **Images** - Vision API analysis (labels, text, objects, faces)
- 🎵 **Audio Files** - Speech-to-Text transcription
- 🎬 **Video Files** - Video Intelligence analysis
- 📊 **JSON & CSV** - Structured data parsing

All searchable through semantic understanding, not just keywords!

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GCS DATA LAKE                           │
│                    (Your Documents)                         │
│  📄 Text  📑 PDF  🖼️ Images  🎵 Audio  🎬 Video  📊 Data    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │  grepctl  │ ← One command orchestration
                    └─────┬─────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Ingestion    │  │ Google APIs  │  │ Processing   │
│ • 6 scripts  │  │ • Vision     │  │ • Extract    │
│ • All types  │  │ • Speech     │  │ • Transform  │
│              │  │ • Video      │  │ • Enrich     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
        └─────────────────┼─────────────────┘
                          ▼
                ┌─────────────────────┐
                │  BigQuery Dataset   │
                │   search_corpus     │
                │  425+ documents     │
                └─────────┬───────────┘
                          ▼
                ┌─────────────────────┐
                │   Vertex AI         │
                │ text-embedding-004  │
                │  768 dimensions     │
                └─────────┬───────────┘
                          ▼
                ┌─────────────────────┐
                │  Semantic Search    │
                │   VECTOR_SEARCH     │
                │  <1 second query    │
                └─────────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Python 3.11+** and **uv** package manager
3. **gcloud CLI** authenticated

### Install grepctl

```bash
# Clone repository
git clone https://github.com/yourusername/bq-semgrep.git
cd bq-semgrep

# Install dependencies
uv sync

# Verify installation
uv run python grepctl.py --help
```

### Complete System Setup

#### Option 1: Fully Automated (Recommended)

```bash
# One command does everything!
uv run python grepctl.py init all --bucket your-bucket --auto-ingest

# This single command:
# 1. Enables 7 Google Cloud APIs
# 2. Creates BigQuery dataset and 3 tables
# 3. Deploys 3 Vertex AI models
# 4. Ingests all files from GCS
# 5. Generates embeddings
# 6. Sets up semantic search
```

#### Option 2: Step-by-Step Control

```bash
# Enable APIs
grepctl apis enable --all

# Initialize BigQuery
grepctl init dataset
grepctl init models

# Ingest data
grepctl ingest all

# Generate embeddings
grepctl index update

# Start searching
grepctl search "your query"
```

## 🔍 Using the System

### Command Line Interface

```bash
# Search with grepctl
grepctl search "machine learning algorithms"
grepctl search "error handling" -k 20 -m pdf -m markdown

# Search with bq-semgrep
uv run bq-semgrep search "data visualization" --top-k 10 --rerank

# Check system status
grepctl status
```

### SQL Interface

```sql
-- Direct semantic search
WITH query_embedding AS (
  SELECT ml_generate_embedding_result AS embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `your-project.mmgrep.text_embedding_model`,
    (SELECT 'machine learning' AS content),
    STRUCT(TRUE AS flatten_json_output)
  )
)
SELECT doc_id, source, text_content, distance AS score
FROM VECTOR_SEARCH(
  TABLE `your-project.mmgrep.search_corpus`,
  'embedding',
  (SELECT embedding FROM query_embedding),
  top_k => 10
)
ORDER BY distance;
```

### Python API

```python
from bq_semgrep.search.vector_search import SemanticSearch

# Initialize searcher
searcher = SemanticSearch(client, config)

# Search across all modalities
results = searcher.search(
    query="neural networks",
    top_k=20,
    source_filter=['pdf', 'images'],
    use_rerank=True
)
```

## 📈 System Capabilities

### Current Status (Production Ready)
- ✅ **425+ documents** indexed across 8 modalities
- ✅ **768-dimensional embeddings** for semantic understanding
- ✅ **Sub-second query response** times
- ✅ **100% embedding coverage** for all documents
- ✅ **5 Google Cloud APIs** integrated
- ✅ **Auto-recovery** from embedding issues

### Supported Operations
| Operation | Command | Description |
|-----------|---------|-------------|
| **Setup** | `grepctl init all --auto-ingest` | Complete one-command setup |
| **Ingest** | `grepctl ingest all` | Process all file types |
| **Index** | `grepctl index update` | Generate embeddings |
| **Fix** | `grepctl fix embeddings` | Auto-fix dimension issues |
| **Search** | `grepctl search "query"` | Semantic search |
| **Status** | `grepctl status` | System health check |

## 🧰 Management Tools

### grepctl - Complete CLI Management

```bash
# System initialization
grepctl init all --bucket your-bucket --auto-ingest

# API management
grepctl apis enable --all
grepctl apis check

# Data ingestion
grepctl ingest pdf        # Process PDFs
grepctl ingest images     # Analyze images with Vision API
grepctl ingest audio      # Transcribe audio
grepctl ingest video      # Analyze videos

# Index management
grepctl index rebuild     # Rebuild from scratch
grepctl index update      # Update missing embeddings
grepctl index verify      # Check embedding health

# Troubleshooting
grepctl fix embeddings    # Fix dimension issues
grepctl fix stuck         # Handle stuck processing
grepctl fix validate      # Check data integrity

# Search
grepctl search "query" -k 20 -o json
```

### Configuration

grepctl uses `~/.grepctl.yaml` for configuration:

```yaml
project_id: your-project
dataset: mmgrep
bucket: your-bucket
location: US
batch_size: 100
chunk_size: 1000
```

## 📊 Supported Data Types

| Modality | Extensions | Processing Method | Google API Used |
|----------|------------|-------------------|-----------------|
| Text | .txt, .log | Direct extraction | — |
| Markdown | .md | Markdown parsing | — |
| PDF | .pdf | OCR extraction | Document AI |
| Images | .jpg, .png, .gif | Visual analysis | Vision API |
| Audio | .mp3, .wav, .m4a | Transcription | Speech-to-Text |
| Video | .mp4, .avi, .mov | Frame + audio analysis | Video Intelligence |
| JSON | .json, .jsonl | Structured parsing | — |
| CSV | .csv, .tsv | Tabular analysis | — |

## 🚀 Advanced Features

### Multimodal Search
Search across all data types simultaneously:
```bash
# Find mentions across PDFs, images, and videos
grepctl search "quarterly revenue" -m pdf -m images -m video
```

### Automatic Processing
- **Vision API** extracts text, labels, objects from images
- **Document AI** performs OCR on scanned PDFs
- **Speech-to-Text** transcribes audio with punctuation
- **Video Intelligence** analyzes frames and transcribes speech

### Error Recovery
```bash
# Automatic fix for common issues
grepctl fix embeddings    # Fixes dimension mismatches
grepctl fix stuck         # Clears stuck processing
```

## 📚 Documentation

- **[grepctl Documentation](grepctl_README.md)** - Complete grepctl usage guide
- **[Architecture Diagrams](visualize_architecture.py)** - System visualization
- **[Lessons Learned](lessons_learned.md)** - Implementation insights
- **[API Integration](api_integration_detail.png)** - Google Cloud API details

## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Permission denied" | Run `gcloud auth login` and ensure BigQuery Admin role |
| "Dataset not found" | Run `grepctl init dataset` |
| "Embedding dimension mismatch" | Run `grepctl fix embeddings` |
| "No search results" | Check `grepctl status` and run `grepctl index update` |
| "API not enabled" | Run `grepctl apis enable --all` |

### Quick Diagnostics

```bash
# Check everything
grepctl status

# Verify APIs
grepctl apis check

# Check embeddings
grepctl index verify

# Fix any issues
grepctl fix embeddings
```

## 🎯 Example Use Cases

1. **Code Search**: Find code patterns across repositories
2. **Document Discovery**: Search PDFs for specific topics
3. **Media Analysis**: Find content in images and videos
4. **Log Analysis**: Semantic search through log files
5. **Data Mining**: Query structured data semantically

## 📈 Performance

- **Ingestion**: ~50 docs/second for text
- **Embedding Generation**: ~20 docs/second
- **Search Latency**: <1 second for most queries
- **Storage**: ~500MB for 425+ documents
- **Accuracy**: 768-dimensional embeddings for semantic precision

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- Google BigQuery ML
- Vertex AI (text-embedding-004)
- Google Cloud Vision, Document AI, Speech-to-Text, Video Intelligence APIs
- Python, uv, and rich CLI library

---

**Ready to search your entire data lake semantically?**

```bash
grepctl init all --bucket your-bucket --auto-ingest
```

🎉 That's all it takes!
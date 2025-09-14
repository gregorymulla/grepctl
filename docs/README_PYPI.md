# grepctl - One-Command Multimodal Semantic Search for BigQuery

🚀 **Deploy a complete semantic search system across your Google Cloud data lake with a single command.**

```bash
# Complete setup in one command
grepctl init all --bucket your-bucket --auto-ingest

# Start searching immediately
grepctl search "find all mentions of machine learning"
```

## What is grepctl?

`grepctl` is a powerful command-line orchestration tool that transforms your Google Cloud Storage data lake into a searchable knowledge base using BigQuery ML and Google Cloud AI services. It handles everything from infrastructure setup to data ingestion and semantic search across 8 different data types.

## ✨ Key Features

- **🎯 One-Command Deployment**: Complete system setup with `grepctl init all`
- **📊 8 Data Modalities**: Text, PDF, Images, Audio, Video, JSON, CSV, Markdown
- **🤖 AI-Powered**: Leverages Vision API, Document AI, Speech-to-Text, and more
- **⚡ Fast Search**: Sub-second semantic queries using BigQuery VECTOR_SEARCH
- **🔧 Auto-Recovery**: Intelligent error handling and dimension mismatch resolution
- **📈 Production Ready**: Successfully processing 400+ documents in production

## 🚀 Quick Start

### Installation

```bash
pip install grepctl
```

### Setup Your System

```bash
# 1. Initialize everything (APIs, BigQuery, Models)
grepctl init all --bucket your-gcs-bucket --auto-ingest

# 2. Check system status
grepctl status

# 3. Start searching!
grepctl search "your semantic query"
```

## 📋 What Gets Created

When you run `grepctl init all`, the tool automatically:

1. **Enables 7 Google Cloud APIs** (BigQuery, Vertex AI, Vision, Document AI, etc.)
2. **Creates BigQuery infrastructure** (dataset, tables, models)
3. **Deploys Vertex AI models** (text-embedding-004 for 768-dim vectors)
4. **Ingests your data** from GCS with modality-specific processing
5. **Generates embeddings** for semantic search
6. **Configures VECTOR_SEARCH** for fast similarity queries

## 🎯 Core Commands

### System Management
```bash
grepctl init all         # Complete one-command setup
grepctl init config      # Configure settings
grepctl apis enable      # Enable required APIs
grepctl status          # Check system health
```

### Data Operations
```bash
grepctl ingest all      # Process all modalities
grepctl ingest pdf      # Process only PDFs
grepctl index update    # Generate embeddings
grepctl index verify    # Check embedding health
```

### Search
```bash
grepctl search "query" -k 20              # Top 20 results
grepctl search "query" -m pdf -m images   # Filter by type
grepctl search "query" -o json            # JSON output
```

### Troubleshooting
```bash
grepctl fix embeddings  # Fix dimension issues
grepctl fix stuck      # Clear stuck processing
```

## 🔧 Configuration

Create `~/.grepctl.yaml`:

```yaml
project_id: your-project
dataset: mmgrep
bucket: your-bucket
location: US
batch_size: 100
chunk_size: 1000
```

## 📊 Supported Data Types

| Type | Extensions | Processing Method |
|------|------------|-------------------|
| Text | .txt, .log | Direct extraction |
| Markdown | .md | Markdown parsing |
| PDF | .pdf | Document AI OCR |
| Images | .jpg, .png | Vision API analysis |
| Audio | .mp3, .wav | Speech-to-Text |
| Video | .mp4, .avi | Video Intelligence |
| JSON | .json | Structured parsing |
| CSV | .csv | Tabular analysis |

## 🚀 Performance

- **Ingestion**: ~50 docs/second for text
- **Embeddings**: ~20 docs/second generation
- **Search**: <1 second query latency
- **Scale**: Handles hundreds of documents efficiently

## 📦 Installation Options

```bash
# Basic installation
pip install grepctl

# With multimedia processing
pip install grepctl[multimedia]

# With development tools
pip install grepctl[dev]

# All features
pip install grepctl[multimedia,dev,research]
```

## 🤝 Requirements

- Python 3.11+
- Google Cloud Project with billing enabled
- Authenticated gcloud CLI
- Appropriate IAM permissions

## 📚 Documentation

- [GitHub Repository](https://github.com/yourusername/grepctl)
- [Full Documentation](https://github.com/yourusername/grepctl#readme)
- [Technical Paper](https://github.com/yourusername/grepctl/blob/main/grepctl_technical_paper.md)

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Permission denied" | Run `gcloud auth login` |
| "Dataset not found" | Run `grepctl init dataset` |
| "Embedding mismatch" | Run `grepctl fix embeddings` |
| "API not enabled" | Run `grepctl apis enable --all` |

## 📄 License

MIT License - see [LICENSE](https://github.com/yourusername/grepctl/blob/main/LICENSE) for details.

## 🙏 Acknowledgments

Built with Google Cloud BigQuery ML, Vertex AI, and the amazing Python ecosystem.

---

**Ready to transform your data lake into a searchable knowledge base?**

```bash
pip install grepctl
grepctl init all --bucket your-bucket --auto-ingest
```

🎉 That's all it takes!
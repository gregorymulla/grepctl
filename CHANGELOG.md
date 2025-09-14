# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-14

### Added
- Initial release of bq-semgrep
- Core Python package with CLI interface (`bq-semgrep`)
- Comprehensive management tool (`grepctl`)
- Support for 8 data modalities:
  - Text and Markdown files
  - PDF documents with OCR (Document AI)
  - Images with Vision API analysis
  - Audio files with Speech-to-Text transcription
  - Video files with Video Intelligence API
  - JSON and CSV structured data
- One-command deployment with `grepctl init all --auto-ingest`
- BigQuery ML integration with Vertex AI embeddings
- 768-dimensional vector embeddings using text-embedding-004
- VECTOR_SEARCH implementation for semantic search
- Automatic error recovery mechanisms
- Dimension mismatch resolution
- Batch processing capabilities
- Rich terminal UI with progress tracking
- Comprehensive configuration management
- Production-ready with sub-second query latency

### Features
- **One-Command Setup**: Complete system initialization with automatic data ingestion
- **Multimodal Search**: Unified semantic search across all data types
- **Auto-Recovery**: Intelligent handling of common errors
- **SQL-Native**: Direct BigQuery integration without external vector databases
- **Cloud-Native**: Leverages 5+ Google Cloud AI services

### Technical Details
- Python 3.11+ support
- Click-based CLI framework
- Rich terminal UI components
- YAML configuration management
- Comprehensive error handling
- Batch processing optimization
- Progress tracking and monitoring

### Documentation
- Complete README with quick start guide
- Technical paper describing architecture
- Lessons learned documentation
- API integration details
- Troubleshooting guide

### Known Limitations
- Vector index not implemented for <5000 documents (not needed at this scale)
- Document AI fails on certain PDF formats (~50% success rate)
- Gemini API integration blocked by permissions (using Document AI as fallback)
- Regional availability limitations for some BigQuery ML features

## [Unreleased]

### Planned
- Multilingual support
- Real-time ingestion capabilities
- Advanced reranking models
- Horizontal scaling for millions of documents
- Cost optimization features
- Web UI for search interface
- Docker containerization
- Kubernetes deployment manifests
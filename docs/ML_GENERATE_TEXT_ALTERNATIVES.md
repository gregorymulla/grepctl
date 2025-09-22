# ML.GENERATE_TEXT Alternatives for grepctl

## Current Status

BigQuery ML does not currently support creating Gemini models as remote models. This is a known limitation that affects the `ML.GENERATE_TEXT` functionality.

## What Works

✅ **Embedding Model**: The text-embedding-004 model is fully functional and provides excellent semantic search capabilities.

✅ **Vector Search**: The VECTOR_SEARCH function works perfectly with the embedding model.

✅ **Text File Ingestion**: Direct ingestion of text, markdown, JSON, and CSV files works without ML.GENERATE_TEXT.

## Limitations

The following features require ML.GENERATE_TEXT and are currently disabled:

- ❌ PDF text extraction
- ❌ Image OCR
- ❌ Audio transcription
- ❌ Video transcription
- ❌ LLM-based reranking

## Alternative Solutions

### For Multimodal Content Processing

1. **Pre-process Files Before Ingestion**
   - Extract text from PDFs using external tools (e.g., Apache Tika, PyPDF2)
   - Perform OCR on images using Vision API separately
   - Transcribe audio/video using Speech-to-Text API
   - Then ingest the extracted text files

2. **Use Cloud Functions**
   - Create Cloud Functions that trigger on file upload to GCS
   - Process files using appropriate APIs (Document AI, Vision, Speech-to-Text)
   - Write extracted text back to GCS or directly to BigQuery

3. **Python Processing Pipeline**
   ```python
   # Example using Vertex AI SDK
   from google.cloud import documentai
   from google.cloud import vision
   from google.cloud import speech

   # Process files before ingestion
   def process_pdf(file_path):
       # Use Document AI to extract text
       pass

   def process_image(file_path):
       # Use Vision API for OCR
       pass

   def process_audio(file_path):
       # Use Speech-to-Text API
       pass
   ```

### For Search Optimization

1. **Semantic Search Only**
   - The embedding model provides excellent semantic search without reranking
   - Results are already sorted by cosine similarity

2. **Hybrid Search**
   - Combine semantic search with keyword search
   - Use the `hybrid_search` method which doesn't require ML.GENERATE_TEXT

3. **Custom Scoring**
   - Implement custom relevance scoring in SQL
   - Use factors like recency, source type, or metadata

## Current Implementation

The system has been updated to:

1. Use embedding-based semantic search as the primary search method
2. Disable reranking when requested (falls back to standard search)
3. Support direct text file ingestion without ML.GENERATE_TEXT
4. Provide clear warnings when ML.GENERATE_TEXT features are requested

## Recommended Workflow

1. **For Text Files**: Ingest directly using `grepctl ingest`
2. **For Multimodal Files**: Pre-process externally, then ingest as text
3. **For Search**: Use standard semantic search without `--rerank` flag

## Example Usage

```bash
# Ingest text files
grepctl ingest --bucket my-bucket --modalities text markdown json csv

# Search using embeddings
grepctl search "your query" --top-k 20

# Use hybrid search for better results
grepctl search "your query" --regex "specific.*pattern"
```

## Future Improvements

When BigQuery ML adds support for Gemini models as remote models:

1. Update the model creation scripts
2. Re-enable multimodal extraction features
3. Re-enable LLM-based reranking

Until then, the embedding-based semantic search provides robust and efficient search capabilities.
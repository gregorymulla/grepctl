# Video Processing Documentation

## Overview

The video processing module in `grepctl` provides comprehensive video analysis capabilities using Google Cloud's Video Intelligence API. It enables semantic search across video content through multiple modalities:

- **Visual Analysis**: Shot detection and scene segmentation
- **Audio Transcription**: Speech-to-text with speaker diarization
- **OCR Detection**: On-screen text extraction
- **Multimodal Embeddings**: Vector representations for semantic search

## Architecture

### Components

1. **Video Processor** (`video_processor.py`)
   - Manages video analysis pipeline
   - Coordinates parallel processing of different modalities
   - Handles embedding generation and storage

2. **Database Schema**
   - `video_metadata`: Core video information and labels
   - `video_segments`: Shot-based segments with visual embeddings
   - `video_transcripts`: Speech transcriptions with timestamps
   - `video_ocr_text`: Detected on-screen text with positions

3. **Search Capabilities**
   - Hybrid search across all modalities
   - Timestamp-based deep linking to specific segments
   - Cross-modal search (text query → visual results)

## Usage

### Setup

Initialize the video processing tables:

```bash
grepctl video --setup
```

This creates the following tables:
- Video metadata storage
- Segment storage with embeddings
- Transcript storage
- OCR text storage

### Processing Videos

Process videos from Google Cloud Storage:

```bash
# Process all videos
grepctl video --process

# Process in smaller batches
grepctl video --process --batch-size 3
```

The processor will:
1. Detect shot boundaries for segmentation
2. Generate visual embeddings for each segment
3. Transcribe audio with speaker identification
4. Extract on-screen text via OCR
5. Detect labels and entities

### Searching Videos

Search across video content:

```bash
# Hybrid search (all modalities)
grepctl video --search "presentation about AI" --search-type hybrid

# Search only transcripts
grepctl video --search "quarterly results" --search-type transcript

# Search on-screen text
grepctl video --search "logo brand" --search-type ocr

# Visual similarity search
grepctl video --search "outdoor scene" --search-type visual
```

### Full Ingestion Pipeline

For end-to-end video processing:

```bash
# 1. Setup tables
grepctl video --setup

# 2. Process videos
grepctl video --process

# 3. Search
grepctl video --search "your query here"
```

## Video Processing Pipeline

### 1. Shot Detection

Videos are segmented based on scene changes:
- Minimum segment duration: 1 second
- Maximum segment duration: 30 seconds
- Long shots are automatically split

### 2. Visual Embeddings

Each segment gets a multimodal embedding:
- 1408-dimensional vectors by default
- Supports 128/256/512 dimensions for optimization
- Cross-modal compatible with text/image embeddings

### 3. Audio Processing

Audio tracks are extracted and transcribed:
- Uses Speech-to-Text v1 for reliability
- Speaker diarization (up to 10 speakers)
- Word-level timestamps
- Automatic punctuation

### 4. OCR Processing

On-screen text is detected and indexed:
- Frame-level text detection
- Bounding box coordinates preserved
- Temporal tracking of text appearances

### 5. Label Detection

Automatic content labeling:
- Entity detection (objects, activities, scenes)
- Hierarchical category labels
- Confidence scores for filtering

## Search Types

### Hybrid Search
Combines all modalities for comprehensive results:
- Searches transcripts, OCR text, and visual content
- Returns deduplicated, ranked results
- Best for general queries

### Transcript Search
Focuses on spoken content:
- Speaker-aware search
- Useful for meetings, lectures, interviews
- Returns segments with speaker IDs

### OCR Search
Targets on-screen text:
- Ideal for presentations, tutorials
- Finds text in slides, signs, UI elements
- Includes frame timestamps

### Visual Search
Semantic visual similarity:
- Cross-modal text → video search
- Finds visually similar segments
- Works with descriptive queries

## Performance Optimization

### Batch Processing
- Configurable batch sizes (default: 5 videos)
- Parallel processing of independent operations
- Progress tracking and error handling

### Embedding Generation
- Cached embeddings to avoid recomputation
- Batch embedding requests for efficiency
- Configurable embedding dimensions

### Storage Optimization
- Partitioned tables by date
- Clustered by video_id for fast lookups
- Compressed metadata storage

## Integration with Existing Pipeline

The video processor integrates seamlessly with the existing `grepctl` infrastructure:

1. **Unified Search Interface**: Video results appear alongside other modalities
2. **Consistent Embedding Space**: Cross-modal search capabilities
3. **Standard CLI Patterns**: Similar commands to audio/image processing

## Limitations and Considerations

1. **File Size**: Videos should be <10GB for optimal processing
2. **Processing Time**: Expect 1-2 minutes per minute of video
3. **Language Support**: Currently optimized for English content
4. **Cost**: Video Intelligence API pricing applies

## Example Workflows

### Educational Content

```bash
# Setup
grepctl video --setup

# Process lecture videos
grepctl video --process --batch-size 10

# Search for specific topics
grepctl video --search "machine learning algorithms" --search-type transcript
grepctl video --search "equation formula" --search-type ocr
```

### Meeting Recordings

```bash
# Process meeting videos
grepctl video --process

# Find discussions by speaker
grepctl video --search "budget discussion" --search-type transcript

# Find shared screens
grepctl video --search "dashboard metrics" --search-type ocr
```

### Content Library

```bash
# Process entire video library
grepctl video --process

# Visual content search
grepctl video --search "sunset beach scene" --search-type visual

# Find branded content
grepctl video --search "company logo" --search-type ocr
```

## Troubleshooting

### Common Issues

1. **API Quota Errors**
   - Solution: Reduce batch size or add delays
   - Check quotas in Cloud Console

2. **Memory Issues**
   - Solution: Process videos in smaller batches
   - Consider using Cloud Run for processing

3. **Poor Transcription Quality**
   - Solution: Ensure good audio quality
   - Specify correct language code

### Debug Commands

```bash
# Check video processing status
grepctl status

# View processing logs
grepctl video --process --batch-size 1  # Process single video for debugging

# Verify table creation
bq ls grepmm | grep video
```

## Future Enhancements

Planned improvements include:

1. **Frame Extraction**: Key frame storage for visual preview
2. **Custom Models**: Fine-tuned embeddings for domain-specific content
3. **Real-time Processing**: Streaming video analysis
4. **Multi-language Support**: Extended language coverage
5. **Activity Recognition**: Temporal action detection
6. **Face Detection**: Privacy-aware person tracking

## API Reference

### VideoProcessor Class

```python
from grepctl.ingestion.video_processor import VideoProcessor

processor = VideoProcessor(client, config)

# Setup tables
processor.create_video_tables()

# Process videos
stats = processor.process_video_files(batch_size=5)

# Search videos
results = processor.search_videos(
    query="search term",
    search_type="hybrid",  # or 'transcript', 'ocr', 'visual'
    top_k=10
)
```

### Configuration

Key configuration parameters in `config.yaml`:

```yaml
# Video processing settings
video:
  min_segment_duration: 1.0
  max_segment_duration: 30.0
  embedding_dimensions: 1408
  batch_size: 5

# API settings
video_intelligence:
  features:
    - shot_detection
    - speech_transcription
    - text_detection
    - label_detection
```

## Cost Estimation

Video Intelligence API pricing (approximate):

- Shot Detection: $0.10 per minute
- Speech Transcription: $0.048 per minute
- Text Detection: $0.15 per minute
- Label Detection: $0.10 per minute

Total: ~$0.40 per minute of video

## Conclusion

The video processing module provides powerful capabilities for making video content searchable through multiple modalities. By combining visual, audio, and text analysis, it enables comprehensive semantic search across video libraries of any size.
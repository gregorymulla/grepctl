#!/usr/bin/env python3
"""
Ingest video files with Video Intelligence API analysis.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from google.cloud import videointelligence_v1 as videointelligence
from google.cloud import speech_v1
from google.cloud import storage
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client(project="semgrep-472018")
video_client = videointelligence.VideoIntelligenceServiceClient()
speech_client = speech_v1.SpeechClient()
bq_client = bigquery.Client(project="semgrep-472018")

def analyze_video(uri: str) -> Optional[str]:
    """Analyze a video file using Video Intelligence API."""

    try:
        logger.info(f"Analyzing video {uri.split('/')[-1]}...")

        # Configure video analysis features
        features = [
            videointelligence.Feature.LABEL_DETECTION,           # What's in the video
            videointelligence.Feature.SHOT_CHANGE_DETECTION,     # Scene changes
            videointelligence.Feature.SPEECH_TRANSCRIPTION,      # Audio transcription
            videointelligence.Feature.TEXT_DETECTION,            # Text/OCR in video
            videointelligence.Feature.OBJECT_TRACKING,           # Track objects
        ]

        # Configure speech transcription
        speech_config = videointelligence.SpeechTranscriptionConfig(
            language_code="en-US",
            enable_automatic_punctuation=True,
        )

        # Configure video context
        video_context = videointelligence.VideoContext(
            speech_transcription_config=speech_config,
        )

        # Start video analysis
        operation = video_client.annotate_video(
            request={
                "input_uri": uri,
                "features": features,
                "video_context": video_context,
            }
        )

        logger.info("Waiting for video analysis to complete (this may take a few minutes)...")
        result = operation.result(timeout=600)  # 10 minute timeout

        # Process results
        filename = uri.split('/')[-1]
        content_parts = [
            f"Video File: {filename}",
            f"Location: {uri}",
            f"Type: Video Content",
            ""
        ]

        # Get first video segment annotation
        if result.annotation_results:
            annotation = result.annotation_results[0]

            # Add video duration
            if annotation.segment:
                duration = annotation.segment.end_time_offset.seconds
                content_parts.append(f"Duration: {duration} seconds")

            # Extract labels (what's in the video)
            if annotation.segment_label_annotations:
                labels = []
                for label in annotation.segment_label_annotations[:20]:
                    category = label.entity.description
                    confidence = label.segments[0].confidence if label.segments else 0
                    labels.append(f"{category} ({confidence:.1%})")

                content_parts.append(f"\nVideo Content Labels:")
                content_parts.append(", ".join(labels[:10]))

            # Extract shot labels (specific scenes)
            if annotation.shot_label_annotations:
                shot_labels = []
                for label in annotation.shot_label_annotations[:15]:
                    shot_labels.append(label.entity.description)

                content_parts.append(f"\nScene Elements:")
                content_parts.append(", ".join(shot_labels[:10]))

            # Extract object tracking
            if annotation.object_annotations:
                objects = []
                for obj in annotation.object_annotations[:10]:
                    obj_name = obj.entity.description
                    confidence = obj.confidence
                    objects.append(f"{obj_name} ({confidence:.1%})")

                content_parts.append(f"\nTracked Objects:")
                content_parts.append(", ".join(objects))

            # Extract text detected in video (OCR)
            if annotation.text_annotations:
                detected_texts = []
                for text_annotation in annotation.text_annotations[:10]:
                    text = text_annotation.text
                    detected_texts.append(text)

                if detected_texts:
                    content_parts.append(f"\nText in Video:")
                    content_parts.append(", ".join(detected_texts[:5]))

            # Extract speech transcription
            transcripts = []
            for speech_transcription in annotation.speech_transcriptions:
                for alternative in speech_transcription.alternatives:
                    if alternative.confidence > 0.5:  # Only high confidence
                        transcripts.append(alternative.transcript)

            if transcripts:
                content_parts.append(f"\nSpeech Transcription:")
                full_transcript = " ".join(transcripts)
                preview = full_transcript[:500] + "..." if len(full_transcript) > 500 else full_transcript
                content_parts.append(preview)

            # Shot change detection (scene count)
            if annotation.shot_annotations:
                content_parts.append(f"\nScene Changes: {len(annotation.shot_annotations)} detected")

            # Add categories
            categories = set()
            for label in annotation.segment_label_annotations[:30]:
                label_lower = label.entity.description.lower()
                if any(word in label_lower for word in ['person', 'people', 'face', 'human']):
                    categories.add("People")
                elif any(word in label_lower for word in ['animal', 'dog', 'cat', 'bird']):
                    categories.add("Animals")
                elif any(word in label_lower for word in ['car', 'vehicle', 'transport']):
                    categories.add("Transportation")
                elif any(word in label_lower for word in ['nature', 'outdoor', 'landscape']):
                    categories.add("Nature")
                elif any(word in label_lower for word in ['sport', 'game', 'activity']):
                    categories.add("Sports")

            if categories:
                content_parts.append(f"\nCategories: {', '.join(categories)}")

        content_parts.extend([
            "",
            "Analysis: Video Intelligence API analysis complete",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"Failed to analyze video {uri}: {e}")
        return None

def analyze_video_simple(uri: str) -> Optional[str]:
    """Simple video analysis with just labels and shot detection."""

    try:
        logger.info(f"Simple analysis for {uri.split('/')[-1]}...")

        # Just get labels and shots (faster)
        features = [
            videointelligence.Feature.LABEL_DETECTION,
            videointelligence.Feature.SHOT_CHANGE_DETECTION,
        ]

        operation = video_client.annotate_video(
            request={
                "input_uri": uri,
                "features": features,
            }
        )

        logger.info("Processing...")
        result = operation.result(timeout=300)

        filename = uri.split('/')[-1]
        content_parts = [
            f"Video File: {filename}",
            f"Location: {uri}",
            f"Type: Video Content",
            ""
        ]

        if result.annotation_results:
            annotation = result.annotation_results[0]

            # Get labels
            if annotation.segment_label_annotations:
                labels = [label.entity.description for label in annotation.segment_label_annotations[:20]]
                content_parts.append(f"Content: {', '.join(labels[:15])}")

            # Shot count
            if annotation.shot_annotations:
                content_parts.append(f"Scenes: {len(annotation.shot_annotations)}")

        content_parts.extend([
            "",
            "Analysis: Video Intelligence (basic) complete",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"Simple analysis failed: {e}")

        # Return metadata only
        filename = uri.split('/')[-1]
        return f"""Video File: {filename}
Location: {uri}
Type: Video Content
Note: Analysis failed - {str(e)[:100]}

This video is indexed with metadata only.

Analysis: Metadata-only indexing
Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""

def insert_video_document(uri: str, text_content: str) -> bool:
    """Insert video document into BigQuery."""

    query = """
    INSERT INTO `semgrep-472018.grepmm.search_corpus` (uri, modality, text_content)
    VALUES (@uri, @modality, @text_content)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('uri', 'STRING', uri),
            bigquery.ScalarQueryParameter('modality', 'STRING', 'video'),
            bigquery.ScalarQueryParameter('text_content', 'STRING', text_content),
        ]
    )

    try:
        job = bq_client.query(query, job_config=job_config)
        job.result()
        return True
    except Exception as e:
        logger.error(f"Failed to insert {uri}: {e}")
        return False

def main():
    """Main function to ingest video files."""

    logger.info("="*70)
    logger.info("Starting Video File Ingestion with Video Intelligence API")
    logger.info("="*70)

    # Check existing videos
    check_query = """
    SELECT COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE modality = 'video'
    """

    try:
        result = bq_client.query(check_query).result()
        existing_count = list(result)[0].count
        if existing_count > 0:
            logger.info(f"Already have {existing_count} video files indexed")
    except:
        existing_count = 0

    # Get list of video files
    bucket = storage_client.bucket("gcm-data-lake")
    blobs = bucket.list_blobs(prefix="multimodal-dataset/video/")
    video_files = [f"gs://gcm-data-lake/{blob.name}" for blob in blobs
                   if blob.name.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]

    logger.info(f"Found {len(video_files)} video files to process")

    # Process each video
    processed_count = 0
    for i, uri in enumerate(video_files, 1):
        logger.info(f"\n[{i}/{len(video_files)}] Processing {uri.split('/')[-1]}...")

        # Try simple analysis first (faster)
        content = analyze_video_simple(uri)

        # If you want full analysis, uncomment:
        # content = analyze_video(uri)

        if content:
            if insert_video_document(uri, content):
                processed_count += 1
                logger.info(f"✓ Successfully processed and indexed")
            else:
                logger.error(f"✗ Failed to insert into BigQuery")
        else:
            logger.error(f"✗ Failed to analyze")

    # Summary
    logger.info("="*70)
    logger.info("Video Ingestion Complete!")
    logger.info("="*70)
    logger.info(f"Successfully processed: {processed_count}/{len(video_files)} video files")

    if processed_count > 0:
        logger.info("\nNext steps:")
        logger.info("1. Generate embeddings: uv run grepctl index --update")
        logger.info("2. Test search: uv run grepctl search 'video scenes objects'")

if __name__ == "__main__":
    main()
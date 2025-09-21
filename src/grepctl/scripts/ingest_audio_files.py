#!/usr/bin/env python3
"""
Ingest audio files with Speech-to-Text transcription.
"""

import logging
import time
from typing import Optional, Dict, Any
from google.cloud import speech_v1
from google.cloud import storage
from google.cloud import bigquery
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client(project="semgrep-472018")
speech_client = speech_v1.SpeechClient()
bq_client = bigquery.Client(project="semgrep-472018")

def transcribe_audio_file(uri: str) -> Optional[str]:
    """Transcribe an audio file using Speech-to-Text API."""

    try:
        logger.info(f"Transcribing {uri.split('/')[-1]}...")

        # Configure audio settings
        audio = speech_v1.RecognitionAudio(uri=uri)

        # Configure recognition settings
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            model="latest_long",  # Better for longer audio
            use_enhanced=True,    # Enhanced model for better accuracy
        )

        # Perform transcription
        operation = speech_client.long_running_recognize(
            config=config,
            audio=audio
        )

        logger.info("Waiting for transcription to complete...")
        response = operation.result(timeout=300)

        # Collect transcription results
        transcription_parts = []
        word_count = 0
        duration_seconds = 0

        for result in response.results:
            # Get the transcript
            transcription_parts.append(result.alternatives[0].transcript)

            # Count words and get duration
            if result.alternatives[0].words:
                word_count += len(result.alternatives[0].words)
                # Get duration from last word timestamp
                last_word = result.alternatives[0].words[-1]
                if last_word.end_time:
                    duration_seconds = max(duration_seconds,
                                          last_word.end_time.seconds +
                                          last_word.end_time.nanos / 1e9)

        full_transcript = ' '.join(transcription_parts)

        # Build content for indexing
        filename = uri.split('/')[-1]
        content_parts = [
            f"Audio File: {filename}",
            f"Location: {uri}",
            f"Type: Audio Recording",
            f"Duration: {duration_seconds:.1f} seconds" if duration_seconds > 0 else "Duration: Unknown",
            f"Word Count: {word_count}" if word_count > 0 else "Word Count: Unknown",
            "",
            "Transcription:",
            full_transcript if full_transcript else "[No speech detected]",
            "",
            f"Analysis: Speech-to-Text transcription complete",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ]

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"Failed to transcribe {uri}: {e}")

        # Return metadata-only content as fallback
        filename = uri.split('/')[-1]
        return f"""Audio File: {filename}
Location: {uri}
Type: Audio Recording
Note: Transcription failed - {str(e)[:100]}

This audio file is indexed with metadata only.
Speech-to-Text API was unable to process this file.

Analysis: Metadata-only indexing
Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""

def transcribe_audio_simple(uri: str) -> Optional[str]:
    """Simple synchronous transcription for short audio files."""

    try:
        logger.info(f"Simple transcription for {uri.split('/')[-1]}...")

        # For short audio files, use synchronous recognition
        audio = speech_v1.RecognitionAudio(uri=uri)

        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.MP3,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )

        # Synchronous recognition (for audio less than 1 minute)
        response = speech_client.recognize(config=config, audio=audio)

        # Get transcription
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "

        filename = uri.split('/')[-1]
        content = f"""Audio File: {filename}
Location: {uri}
Type: Audio Recording (Short)

Transcription:
{transcript.strip() if transcript else "[No speech detected]"}

Analysis: Speech-to-Text transcription complete
Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""

        return content

    except Exception as e:
        logger.error(f"Simple transcription failed: {e}")
        return None

def insert_audio_document(uri: str, text_content: str) -> bool:
    """Insert audio document into BigQuery."""

    query = """
    INSERT INTO `semgrep-472018.grepmm.search_corpus` (uri, modality, text_content)
    VALUES (@uri, @modality, @text_content)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('uri', 'STRING', uri),
            bigquery.ScalarQueryParameter('modality', 'STRING', 'audio'),
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
    """Main function to ingest audio files."""

    logger.info("="*70)
    logger.info("Starting Audio File Ingestion with Speech-to-Text")
    logger.info("="*70)

    # Check if audio files already exist
    check_query = """
    SELECT COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE modality = 'audio'
    """

    try:
        result = bq_client.query(check_query).result()
        existing_count = list(result)[0].count
        if existing_count > 0:
            logger.info(f"Already have {existing_count} audio files indexed")
    except:
        existing_count = 0

    # Get list of audio files
    bucket = storage_client.bucket("gcm-data-lake")
    blobs = bucket.list_blobs(prefix="multimodal-dataset/audio/")
    audio_files = [f"gs://gcm-data-lake/{blob.name}" for blob in blobs
                   if blob.name.endswith(('.mp3', '.wav', '.flac', '.m4a'))]

    logger.info(f"Found {len(audio_files)} audio files to process")

    # Process each audio file
    processed_count = 0
    for uri in audio_files:
        logger.info(f"\nProcessing {uri.split('/')[-1]}...")

        # Try simple transcription first (faster for short files)
        content = transcribe_audio_simple(uri)

        # If simple fails, try long-running recognition
        if not content:
            content = transcribe_audio_file(uri)

        if content:
            if insert_audio_document(uri, content):
                processed_count += 1
                logger.info(f"✓ Successfully processed and indexed")
            else:
                logger.error(f"✗ Failed to insert into BigQuery")
        else:
            logger.error(f"✗ Failed to transcribe")

    # Summary
    logger.info("="*70)
    logger.info("Audio Ingestion Complete!")
    logger.info("="*70)
    logger.info(f"Successfully processed: {processed_count}/{len(audio_files)} audio files")

    if processed_count > 0:
        logger.info("\nNext steps:")
        logger.info("1. Generate embeddings: uv run grepctl index --update")
        logger.info("2. Test search: uv run grepctl search 'audio speech transcription'")

if __name__ == "__main__":
    main()
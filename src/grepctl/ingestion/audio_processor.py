"""
Audio processing and transcription for semantic search.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from google.cloud import speech_v2
from google.cloud import speech_v1
from google.cloud import storage
from google.api_core import exceptions as api_exceptions

from ..config import Config
from ..bigquery.connection import BigQueryClient

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Process audio files with transcription and semantic chunking."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize audio processor."""
        self.client = client
        self.config = config
        self.storage_client = storage.Client(project=config.project_id)

        # Initialize Speech clients
        self.speech_client_v1 = speech_v1.SpeechClient()
        self.speech_client_v2 = speech_v2.SpeechClient()

        # Audio processing settings
        self.short_audio_threshold = 60  # seconds
        self.chunk_size = 500  # tokens for audio chunks
        self.chunk_overlap = 100  # tokens overlap

    def create_audio_metadata_table(self) -> None:
        """Create table for storing audio metadata and speaker segments."""
        logger.info("Creating audio metadata table...")

        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.audio_metadata` (
            audio_id STRING NOT NULL,
            uri STRING NOT NULL,
            duration_seconds FLOAT64,
            speaker_count INT64,
            transcription_confidence FLOAT64,
            speaker_segments ARRAY<STRUCT<
                speaker_id STRING,
                start_time FLOAT64,
                end_time FLOAT64,
                text STRING,
                confidence FLOAT64
            >>,
            word_timestamps ARRAY<STRUCT<
                word STRING,
                start_time FLOAT64,
                end_time FLOAT64,
                speaker_id STRING
            >>,
            processing_metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        PARTITION BY DATE(created_at)
        CLUSTER BY uri
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Audio metadata table created successfully")
        except Exception as e:
            logger.error(f"Failed to create audio metadata table: {e}")
            raise

    def process_audio_files(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process audio files from GCS with transcription."""
        logger.info("Starting audio file processing...")

        stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_failed': 0,
            'total_duration_seconds': 0,
            'chunks_created': 0
        }

        # Get list of audio files from GCS
        audio_files = self._list_audio_files()
        logger.info(f"Found {len(audio_files)} audio files to process")

        # Check for already processed files
        processed_uris = self._get_processed_uris()
        new_files = [f for f in audio_files if f not in processed_uris]
        logger.info(f"Processing {len(new_files)} new audio files")

        # Process files in batches
        for i in range(0, len(new_files), batch_size):
            batch = new_files[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} files)")

            for audio_uri in batch:
                try:
                    result = self._process_single_audio(audio_uri)
                    if result:
                        stats['files_processed'] += 1
                        stats['total_duration_seconds'] += result.get('duration', 0)
                        stats['chunks_created'] += result.get('chunks', 0)
                except Exception as e:
                    logger.error(f"Failed to process {audio_uri}: {e}")
                    stats['files_failed'] += 1

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Audio processing complete. Processed {stats['files_processed']} files")
        return stats

    def _list_audio_files(self) -> List[str]:
        """List audio files from GCS bucket."""
        bucket = self.storage_client.bucket(self.config.gcs_bucket)
        prefix = f"{self.config.gcs_prefix}/audio/"

        audio_extensions = self.config.modality_extensions.get('audio', [])
        audio_files = []

        for blob in bucket.list_blobs(prefix=prefix):
            if any(blob.name.endswith(ext) for ext in audio_extensions):
                audio_files.append(f"gs://{self.config.gcs_bucket}/{blob.name}")

        return audio_files

    def _get_processed_uris(self) -> set:
        """Get set of already processed audio URIs."""
        query = f"""
        SELECT DISTINCT uri
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        WHERE modality = 'audio'
        """

        try:
            results = self.client.execute_query_and_wait(query)
            return {row['uri'] for row in results}
        except:
            return set()

    def _process_single_audio(self, audio_uri: str) -> Optional[Dict[str, Any]]:
        """Process a single audio file."""
        logger.info(f"Processing audio file: {audio_uri.split('/')[-1]}")

        # Get audio file info
        audio_info = self._get_audio_info(audio_uri)

        # Choose transcription method based on duration
        if audio_info.get('duration_seconds', 0) <= self.short_audio_threshold:
            transcription = self._transcribe_short_audio(audio_uri)
        else:
            transcription = self._transcribe_long_audio(audio_uri)

        if not transcription:
            logger.warning(f"Failed to transcribe {audio_uri}")
            return None

        # Create chunks from transcription
        chunks = self._create_audio_chunks(transcription, audio_uri)

        # Insert documents and metadata
        self._insert_audio_documents(audio_uri, chunks, transcription)

        # Store metadata
        self._store_audio_metadata(audio_uri, transcription)

        return {
            'uri': audio_uri,
            'duration': transcription.get('duration_seconds', 0),
            'chunks': len(chunks),
            'speakers': transcription.get('speaker_count', 1)
        }

    def _get_audio_info(self, audio_uri: str) -> Dict[str, Any]:
        """Get basic information about an audio file."""
        # For now, return basic info
        # Could be enhanced with actual audio analysis
        return {
            'uri': audio_uri,
            'filename': audio_uri.split('/')[-1],
            'duration_seconds': 120  # Default estimate, will be updated during transcription
        }

    def _transcribe_short_audio(self, audio_uri: str) -> Optional[Dict[str, Any]]:
        """Transcribe short audio files (<1 minute) using synchronous API."""
        logger.info(f"Using synchronous transcription for {audio_uri.split('/')[-1]}")

        try:
            audio = speech_v1.RecognitionAudio(uri=audio_uri)

            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=None,  # Auto-detect sample rate
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                diarization_config=speech_v1.SpeakerDiarizationConfig(
                    enable_speaker_diarization=True,
                    min_speaker_count=1,
                    max_speaker_count=10
                ),
                model="latest_long",
                use_enhanced=True
            )

            response = self.speech_client_v1.recognize(config=config, audio=audio)

            return self._parse_speech_response(response, audio_uri)

        except Exception as e:
            logger.error(f"Synchronous transcription failed: {e}")
            return None

    def _transcribe_long_audio(self, audio_uri: str) -> Optional[Dict[str, Any]]:
        """Transcribe long audio files - directly use v1 API since v2 requires recognizer setup."""
        logger.info(f"Using long-running transcription for {audio_uri.split('/')[-1]}")
        # Directly use v1 API which is more straightforward
        return self._transcribe_long_audio_v1(audio_uri)

    def _transcribe_long_audio_v1(self, audio_uri: str) -> Optional[Dict[str, Any]]:
        """Fallback transcription using v1 long running recognize."""
        logger.info(f"Using v1 long running recognition for {audio_uri.split('/')[-1]}")

        try:
            audio = speech_v1.RecognitionAudio(uri=audio_uri)

            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=None,  # Auto-detect sample rate
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                diarization_config=speech_v1.SpeakerDiarizationConfig(
                    enable_speaker_diarization=True,
                    min_speaker_count=1,
                    max_speaker_count=10
                ),
                model="latest_long",
                use_enhanced=True
            )

            operation = self.speech_client_v1.long_running_recognize(
                config=config,
                audio=audio
            )

            logger.info("Waiting for transcription to complete...")
            response = operation.result(timeout=600)

            return self._parse_speech_response(response, audio_uri)

        except Exception as e:
            logger.error(f"V1 long running recognition failed: {e}")
            return None

    def _parse_speech_response(self, response: Any, audio_uri: str) -> Dict[str, Any]:
        """Parse Speech API v1 response."""
        transcription_parts = []
        word_timestamps = []
        speaker_segments = []
        total_confidence = 0
        num_results = 0
        duration_seconds = 0

        for result in response.results:
            if not result.alternatives:
                continue

            best_alternative = result.alternatives[0]
            transcription_parts.append(best_alternative.transcript)

            if best_alternative.confidence:
                total_confidence += best_alternative.confidence
                num_results += 1

            # Extract word timestamps
            for word_info in best_alternative.words:
                word_data = {
                    'word': word_info.word,
                    'start_time': word_info.start_time.total_seconds() if word_info.start_time else 0,
                    'end_time': word_info.end_time.total_seconds() if word_info.end_time else 0,
                    'speaker_id': str(word_info.speaker_tag) if hasattr(word_info, 'speaker_tag') else '0'
                }
                word_timestamps.append(word_data)

                # Update duration
                if word_info.end_time:
                    duration_seconds = max(duration_seconds, word_info.end_time.total_seconds())

        # Combine transcriptions
        full_transcript = ' '.join(transcription_parts)

        # Group by speaker segments
        if word_timestamps:
            speaker_segments = self._group_speaker_segments(word_timestamps)

        return {
            'transcript': full_transcript,
            'duration_seconds': duration_seconds,
            'confidence': total_confidence / num_results if num_results > 0 else 0,
            'word_timestamps': word_timestamps,
            'speaker_segments': speaker_segments,
            'speaker_count': len(set(w['speaker_id'] for w in word_timestamps)) if word_timestamps else 1,
            'uri': audio_uri
        }

    def _parse_batch_response(self, result: Any, audio_uri: str) -> Dict[str, Any]:
        """Parse Speech API v2 batch response."""
        transcript_text = result.transcript.results[0].alternatives[0].transcript if result.transcript.results else ""

        # Extract metadata if available
        word_timestamps = []
        if result.transcript.results:
            for res in result.transcript.results:
                if res.alternatives and res.alternatives[0].words:
                    for word in res.alternatives[0].words:
                        word_timestamps.append({
                            'word': word.word,
                            'start_time': word.start_offset.total_seconds() if word.start_offset else 0,
                            'end_time': word.end_offset.total_seconds() if word.end_offset else 0,
                            'speaker_id': str(word.speaker_label) if hasattr(word, 'speaker_label') else '0'
                        })

        duration_seconds = max((w['end_time'] for w in word_timestamps), default=0)
        speaker_segments = self._group_speaker_segments(word_timestamps) if word_timestamps else []

        return {
            'transcript': transcript_text,
            'duration_seconds': duration_seconds,
            'confidence': 0.95,  # Default high confidence for v2
            'word_timestamps': word_timestamps,
            'speaker_segments': speaker_segments,
            'speaker_count': len(set(w['speaker_id'] for w in word_timestamps)) if word_timestamps else 1,
            'uri': audio_uri
        }

    def _group_speaker_segments(self, word_timestamps: List[Dict]) -> List[Dict]:
        """Group word timestamps into speaker segments."""
        if not word_timestamps:
            return []

        segments = []
        current_segment = {
            'speaker_id': word_timestamps[0]['speaker_id'],
            'start_time': word_timestamps[0]['start_time'],
            'end_time': word_timestamps[0]['end_time'],
            'words': [word_timestamps[0]['word']],
            'confidence': 0.95
        }

        for word in word_timestamps[1:]:
            if word['speaker_id'] == current_segment['speaker_id']:
                # Continue current segment
                current_segment['words'].append(word['word'])
                current_segment['end_time'] = word['end_time']
            else:
                # Save current segment and start new one
                current_segment['text'] = ' '.join(current_segment['words'])
                del current_segment['words']
                segments.append(current_segment)

                current_segment = {
                    'speaker_id': word['speaker_id'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time'],
                    'words': [word['word']],
                    'confidence': 0.95
                }

        # Add last segment
        if current_segment:
            current_segment['text'] = ' '.join(current_segment['words'])
            del current_segment['words']
            segments.append(current_segment)

        return segments

    def _create_audio_chunks(self, transcription: Dict[str, Any], audio_uri: str) -> List[Dict[str, Any]]:
        """Create semantic chunks from audio transcription."""
        chunks = []
        full_text = transcription['transcript']

        if not full_text:
            return chunks

        # Use speaker segments if available
        if transcription.get('speaker_segments'):
            for i, segment in enumerate(transcription['speaker_segments']):
                chunk_text = f"[Speaker {segment['speaker_id']}] {segment['text']}"

                chunk = {
                    'chunk_index': i,
                    'text': chunk_text,
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'speaker_id': segment['speaker_id'],
                    'metadata': {
                        'audio_uri': audio_uri,
                        'duration': segment['end_time'] - segment['start_time'],
                        'speaker': segment['speaker_id']
                    }
                }
                chunks.append(chunk)
        else:
            # Fall back to simple text chunking
            words = full_text.split()
            chunk_words = []
            chunk_index = 0

            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = ' '.join(chunk_words)

                chunk = {
                    'chunk_index': chunk_index,
                    'text': chunk_text,
                    'start_time': 0,
                    'end_time': transcription.get('duration_seconds', 0),
                    'metadata': {
                        'audio_uri': audio_uri,
                        'duration': transcription.get('duration_seconds', 0)
                    }
                }
                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def _insert_audio_documents(self, audio_uri: str, chunks: List[Dict], transcription: Dict) -> None:
        """Insert audio documents and chunks into BigQuery."""
        filename = audio_uri.split('/')[-1]

        # Create searchable content
        content_parts = [
            f"Audio File: {filename}",
            f"Duration: {transcription.get('duration_seconds', 0):.1f} seconds",
            f"Speakers: {transcription.get('speaker_count', 1)}",
            f"Confidence: {transcription.get('confidence', 0):.1%}",
            "",
            "Transcription:",
            transcription['transcript'][:2000] + "..." if len(transcription['transcript']) > 2000 else transcription['transcript'],
            "",
            f"Indexed: {datetime.utcnow().isoformat()}"
        ]

        full_content = '\n'.join(content_parts)

        # Insert main document
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        (doc_id, uri, modality, source, created_at, text_content, meta)
        VALUES (
            GENERATE_UUID(),
            @uri,
            'audio',
            'audio',
            CURRENT_TIMESTAMP(),
            @text_content,
            @meta
        )
        """

        meta_data = {
            'duration_seconds': transcription.get('duration_seconds', 0),
            'speaker_count': transcription.get('speaker_count', 1),
            'confidence': transcription.get('confidence', 0),
            'chunk_count': len(chunks)
        }

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter('uri', 'STRING', audio_uri),
                bigquery.ScalarQueryParameter('text_content', 'STRING', full_content),
                bigquery.ScalarQueryParameter('meta', 'JSON', json.dumps(meta_data))
            ]
        )

        try:
            self.client.client.query(query, job_config=job_config).result()
            logger.info(f"Inserted audio document for {filename}")
        except Exception as e:
            logger.error(f"Failed to insert audio document: {e}")

        # Insert chunks
        if chunks:
            self._insert_audio_chunks(audio_uri, chunks)

    def _insert_audio_chunks(self, audio_uri: str, chunks: List[Dict]) -> None:
        """Insert audio chunks for better search granularity."""
        for chunk in chunks:
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.document_chunks`
            (doc_id, uri, modality, source, created_at, text_content, chunk_index, meta)
            VALUES (
                GENERATE_UUID(),
                @uri,
                'audio',
                'audio',
                CURRENT_TIMESTAMP(),
                @text_content,
                @chunk_index,
                @meta
            )
            """

            from google.cloud import bigquery

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter('uri', 'STRING', audio_uri),
                    bigquery.ScalarQueryParameter('text_content', 'STRING', chunk['text']),
                    bigquery.ScalarQueryParameter('chunk_index', 'INT64', chunk['chunk_index']),
                    bigquery.ScalarQueryParameter('meta', 'JSON', json.dumps(chunk.get('metadata', {})))
                ]
            )

            try:
                self.client.client.query(query, job_config=job_config).result()
            except Exception as e:
                logger.error(f"Failed to insert chunk {chunk['chunk_index']}: {e}")

    def _store_audio_metadata(self, audio_uri: str, transcription: Dict) -> None:
        """Store detailed audio metadata."""
        from google.cloud import bigquery

        # Prepare speaker segments for BigQuery
        speaker_segments = []
        for seg in transcription.get('speaker_segments', []):
            speaker_segments.append({
                'speaker_id': seg['speaker_id'],
                'start_time': seg['start_time'],
                'end_time': seg['end_time'],
                'text': seg['text'],
                'confidence': seg.get('confidence', 0.95)
            })

        # Prepare word timestamps
        word_timestamps = transcription.get('word_timestamps', [])

        processing_metadata = {
            'processed_at': datetime.utcnow().isoformat(),
            'model': 'speech-to-text-v1',
            'language': 'en-US'
        }

        # Build query based on whether we have segments/timestamps
        if speaker_segments and word_timestamps:
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.audio_metadata`
            (audio_id, uri, duration_seconds, speaker_count, transcription_confidence,
             speaker_segments, word_timestamps, processing_metadata)
            VALUES (
                GENERATE_UUID(),
                @uri,
                @duration,
                @speaker_count,
                @confidence,
                @speaker_segments,
                @word_timestamps,
                @processing_metadata
            )
            """
        elif speaker_segments:
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.audio_metadata`
            (audio_id, uri, duration_seconds, speaker_count, transcription_confidence,
             speaker_segments, processing_metadata)
            VALUES (
                GENERATE_UUID(),
                @uri,
                @duration,
                @speaker_count,
                @confidence,
                @speaker_segments,
                @processing_metadata
            )
            """
        elif word_timestamps:
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.audio_metadata`
            (audio_id, uri, duration_seconds, speaker_count, transcription_confidence,
             word_timestamps, processing_metadata)
            VALUES (
                GENERATE_UUID(),
                @uri,
                @duration,
                @speaker_count,
                @confidence,
                @word_timestamps,
                @processing_metadata
            )
            """
        else:
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.audio_metadata`
            (audio_id, uri, duration_seconds, speaker_count, transcription_confidence,
             processing_metadata)
            VALUES (
                GENERATE_UUID(),
                @uri,
                @duration,
                @speaker_count,
                @confidence,
                @processing_metadata
            )
            """

        # Build query parameters based on available data
        query_params = [
            bigquery.ScalarQueryParameter('uri', 'STRING', audio_uri),
            bigquery.ScalarQueryParameter('duration', 'FLOAT64', transcription.get('duration_seconds', 0)),
            bigquery.ScalarQueryParameter('speaker_count', 'INT64', transcription.get('speaker_count', 1)),
            bigquery.ScalarQueryParameter('confidence', 'FLOAT64', transcription.get('confidence', 0)),
            bigquery.ScalarQueryParameter('processing_metadata', 'JSON', json.dumps(processing_metadata))
        ]

        # Only add array parameters if they're not empty and part of the query
        if speaker_segments:
            # Create structured values for BigQuery
            segment_values = []
            for seg in speaker_segments:
                segment_values.append(bigquery.StructQueryParameter(
                    None,
                    bigquery.ScalarQueryParameter('speaker_id', 'STRING', seg['speaker_id']),
                    bigquery.ScalarQueryParameter('start_time', 'FLOAT64', seg['start_time']),
                    bigquery.ScalarQueryParameter('end_time', 'FLOAT64', seg['end_time']),
                    bigquery.ScalarQueryParameter('text', 'STRING', seg['text']),
                    bigquery.ScalarQueryParameter('confidence', 'FLOAT64', seg['confidence'])
                ))
            query_params.append(bigquery.ArrayQueryParameter('speaker_segments', 'STRUCT', segment_values))

        if word_timestamps:
            # Create structured values for BigQuery
            word_values = []
            for word in word_timestamps:
                word_values.append(bigquery.StructQueryParameter(
                    None,
                    bigquery.ScalarQueryParameter('word', 'STRING', word['word']),
                    bigquery.ScalarQueryParameter('start_time', 'FLOAT64', word['start_time']),
                    bigquery.ScalarQueryParameter('end_time', 'FLOAT64', word['end_time']),
                    bigquery.ScalarQueryParameter('speaker_id', 'STRING', word.get('speaker_id', '0'))
                ))
            query_params.append(bigquery.ArrayQueryParameter('word_timestamps', 'STRUCT', word_values))

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        try:
            self.client.client.query(query, job_config=job_config).result()
            logger.info(f"Stored metadata for {audio_uri}")
        except Exception as e:
            logger.error(f"Failed to store audio metadata: {e}")

    def update_search_corpus(self) -> int:
        """Update search corpus with audio documents."""
        logger.info("Updating search corpus with audio documents...")

        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        SELECT * FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        WHERE modality = 'audio'
        AND uri NOT IN (
            SELECT uri FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            WHERE modality = 'audio'
        )
        """

        try:
            job = self.client.client.query(query)
            job.result()
            rows_added = job.num_dml_affected_rows or 0
            logger.info(f"Added {rows_added} audio documents to search corpus")
            return rows_added
        except Exception as e:
            logger.error(f"Failed to update search corpus: {e}")
            return 0
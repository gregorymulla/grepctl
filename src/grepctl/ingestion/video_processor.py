"""
Video processing with shot detection, multimodal embeddings, and OCR.
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from google.cloud import videointelligence_v1
from google.cloud import aiplatform
from google.cloud import storage
from google.api_core import operations_v1
from google.api_core import exceptions as api_exceptions

from ..config import Config
from ..bigquery.connection import BigQueryClient
from .audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


@dataclass
class VideoSegment:
    """Represents a video segment with metadata."""
    segment_id: str
    start_time: float
    end_time: float
    duration: float
    shot_label: Optional[str] = None
    confidence: float = 0.0
    frame_rate: Optional[float] = None
    key_frame_uri: Optional[str] = None
    visual_embedding: Optional[List[float]] = None
    transcript_text: Optional[str] = None
    ocr_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoProcessor:
    """Process video files with comprehensive analysis."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize video processor."""
        self.client = client
        self.config = config
        self.storage_client = storage.Client(project=config.project_id)
        self.audio_processor = AudioProcessor(client, config)

        # Initialize Video Intelligence client
        self.video_client = videointelligence_v1.VideoIntelligenceServiceClient()

        # Initialize Vertex AI for embeddings
        vertex_location = getattr(config, 'vertex_location', config.location)
        if vertex_location == 'US':
            vertex_location = 'us-central1'  # Convert US to valid Vertex region
        aiplatform.init(project=config.project_id, location=vertex_location)

        # Video processing settings
        self.min_segment_duration = 1.0  # Minimum segment duration in seconds
        self.max_segment_duration = 30.0  # Maximum segment duration
        self.embedding_dimensions = 1408  # Multimodal embedding dimensions
        self.batch_size = 10
        self.enable_ocr = False  # Disable OCR by default to save costs
        self.enable_labels = False  # Disable label detection by default
        self.sample_rate = 0.1  # Sample 10% of frames (1 frame every 10 frames)
        self.max_frames_per_video = 100  # Maximum frames to process per video
        self.segment_sample_interval = 10  # Process one segment every N seconds

    def create_video_tables(self) -> None:
        """Create all necessary video processing tables."""
        logger.info("Creating video processing tables...")

        # Video metadata table
        self._create_video_metadata_table()

        # Video segments table
        self._create_video_segments_table()

        # Video transcripts table
        self._create_video_transcripts_table()

        # Video OCR text table
        self._create_video_ocr_table()

        logger.info("Video processing tables created successfully")

    def _create_video_metadata_table(self) -> None:
        """Create table for video metadata."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.video_metadata` (
            video_id STRING NOT NULL,
            uri STRING NOT NULL,
            duration_seconds FLOAT64,
            frame_rate FLOAT64,
            width INT64,
            height INT64,
            codec STRING,
            segment_count INT64,
            shot_changes ARRAY<FLOAT64>,
            labels ARRAY<STRUCT<
                entity_id STRING,
                description STRING,
                language_code STRING,
                category_entities ARRAY<STRUCT<
                    entity_id STRING,
                    description STRING
                >>,
                segments ARRAY<STRUCT<
                    start_time FLOAT64,
                    end_time FLOAT64,
                    confidence FLOAT64
                >>
            >>,
            processing_metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        PARTITION BY DATE(created_at)
        CLUSTER BY uri
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Video metadata table created")
        except Exception as e:
            logger.error(f"Failed to create video metadata table: {e}")
            raise

    def _create_video_segments_table(self) -> None:
        """Create table for video segments."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.video_segments` (
            segment_id STRING NOT NULL,
            video_id STRING NOT NULL,
            uri STRING NOT NULL,
            segment_index INT64,
            start_time FLOAT64,
            end_time FLOAT64,
            duration FLOAT64,
            shot_label STRING,
            confidence FLOAT64,
            visual_embedding ARRAY<FLOAT64>,
            embedding_model STRING,
            key_frame_uri STRING,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        PARTITION BY DATE(created_at)
        CLUSTER BY video_id, segment_index
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Video segments table created")
        except Exception as e:
            logger.error(f"Failed to create video segments table: {e}")
            raise

    def _create_video_transcripts_table(self) -> None:
        """Create table for video transcripts."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.video_transcripts` (
            transcript_id STRING NOT NULL,
            video_id STRING NOT NULL,
            uri STRING NOT NULL,
            segment_id STRING,
            start_time FLOAT64,
            end_time FLOAT64,
            speaker_id STRING,
            text STRING,
            confidence FLOAT64,
            word_timestamps ARRAY<STRUCT<
                word STRING,
                start_time FLOAT64,
                end_time FLOAT64,
                confidence FLOAT64
            >>,
            text_embedding ARRAY<FLOAT64>,
            language_code STRING DEFAULT 'en-US',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        PARTITION BY DATE(created_at)
        CLUSTER BY video_id
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Video transcripts table created")
        except Exception as e:
            logger.error(f"Failed to create video transcripts table: {e}")
            raise

    def _create_video_ocr_table(self) -> None:
        """Create table for OCR text from video frames."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.video_ocr_text` (
            ocr_id STRING NOT NULL,
            video_id STRING NOT NULL,
            uri STRING NOT NULL,
            segment_id STRING,
            frame_time FLOAT64,
            text STRING,
            confidence FLOAT64,
            bounding_box STRUCT<
                left_x FLOAT64,
                top_y FLOAT64,
                right_x FLOAT64,
                bottom_y FLOAT64
            >,
            text_embedding ARRAY<FLOAT64>,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        PARTITION BY DATE(created_at)
        CLUSTER BY video_id
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Video OCR text table created")
        except Exception as e:
            logger.error(f"Failed to create video OCR text table: {e}")
            raise

    def estimate_processing_cost(self, video_duration_minutes: float, mode: str = 'efficient') -> Dict[str, float]:
        """
        Estimate processing cost for video analysis.

        Args:
            video_duration_minutes: Video duration in minutes
            mode: Processing mode

        Returns:
            Cost breakdown by feature
        """
        costs = {
            'shot_detection': 0.10 * video_duration_minutes,
            'speech_transcription': 0.048 * video_duration_minutes,
            'text_detection': 0.0,
            'label_detection': 0.0,
            'total': 0.0
        }

        if mode == 'minimal':
            # Minimal: shots + speech, heavy sampling
            sampling_factor = 0.3  # Process ~30% due to sampling
            costs['shot_detection'] *= sampling_factor
            costs['speech_transcription'] *= sampling_factor

        elif mode == 'efficient':
            # Efficient: shots + speech, moderate sampling
            sampling_factor = 0.5  # Process ~50% due to sampling
            costs['shot_detection'] *= sampling_factor
            costs['speech_transcription'] *= sampling_factor

        elif mode == 'full':
            # Full: everything, no sampling
            costs['text_detection'] = 0.15 * video_duration_minutes
            costs['label_detection'] = 0.10 * video_duration_minutes

        costs['total'] = sum(v for k, v in costs.items() if k != 'total')
        return costs

    def process_video_files(self, batch_size: Optional[int] = None,
                           sample_mode: str = 'efficient') -> Dict[str, Any]:
        """
        Process video files from GCS with comprehensive analysis.

        Args:
            batch_size: Number of videos to process at once
            sample_mode: Processing mode - 'efficient' (sample), 'full' (all frames), 'minimal' (shots only)
        """
        logger.info(f"Starting video file processing in {sample_mode} mode...")

        if batch_size is None:
            batch_size = self.batch_size

        # Configure settings based on mode
        if sample_mode == 'minimal':
            self.enable_ocr = False
            self.enable_labels = False
            self.segment_sample_interval = 30  # Sample every 30 seconds
            logger.info("Minimal mode: Shot detection + basic transcription only")
        elif sample_mode == 'efficient':
            self.enable_ocr = False
            self.enable_labels = False
            self.segment_sample_interval = 10  # Sample every 10 seconds
            logger.info("Efficient mode: Balanced processing with sampling")
        elif sample_mode == 'full':
            self.enable_ocr = True
            self.enable_labels = True
            self.segment_sample_interval = 0  # Process all segments
            logger.info("Full mode: Complete analysis (higher cost)")
        else:
            logger.warning(f"Unknown mode {sample_mode}, using efficient mode")

        stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_failed': 0,
            'total_duration_seconds': 0,
            'segments_created': 0,
            'transcripts_created': 0,
            'ocr_detections': 0
        }

        # Get list of video files
        video_files = self._list_video_files()
        logger.info(f"Found {len(video_files)} video files to process")

        # Check for already processed files
        processed_uris = self._get_processed_uris()
        new_files = [f for f in video_files if f not in processed_uris]
        logger.info(f"Processing {len(new_files)} new video files")

        # Process files in batches
        for i in range(0, len(new_files), batch_size):
            batch = new_files[i:i+batch_size]
            batch_num = i//batch_size + 1
            logger.info(f"Processing batch {batch_num} ({len(batch)} files)")

            for j, video_uri in enumerate(batch):
                video_name = video_uri.split('/')[-1]
                video_number = i + j + 1
                logger.info(f"[{video_number}/{len(new_files)}] Processing: {video_name}")

                try:
                    result = self._process_single_video(video_uri)
                    if result:
                        stats['files_processed'] += 1
                        stats['total_duration_seconds'] += result.get('duration', 0)
                        stats['segments_created'] += result.get('segments', 0)
                        stats['transcripts_created'] += result.get('transcripts', 0)
                        stats['ocr_detections'] += result.get('ocr_detections', 0)
                        logger.info(f"[{video_number}/{len(new_files)}] ✓ Completed: {video_name}")
                except Exception as e:
                    logger.error(f"Failed to process {video_uri}: {e}")
                    stats['files_failed'] += 1

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Video processing complete. Processed {stats['files_processed']} files")
        logger.info(f"Created {stats['segments_created']} segments, {stats['transcripts_created']} transcripts")

        return stats

    def _list_video_files(self) -> List[str]:
        """List video files from GCS bucket."""
        bucket = self.storage_client.bucket(self.config.gcs_bucket)
        prefix = f"{self.config.gcs_prefix}/video/"

        video_extensions = self.config.modality_extensions.get('video', [])
        video_files = []

        for blob in bucket.list_blobs(prefix=prefix):
            if any(blob.name.endswith(ext) for ext in video_extensions):
                video_files.append(f"gs://{self.config.gcs_bucket}/{blob.name}")

        return video_files

    def _get_processed_uris(self) -> set:
        """Get set of already processed video URIs."""
        query = f"""
        SELECT DISTINCT uri
        FROM `{self.config.project_id}.{self.config.dataset_name}.video_metadata`
        """

        try:
            results = self.client.execute_query_and_wait(query)
            return {row['uri'] for row in results}
        except:
            return set()

    def _process_single_video(self, video_uri: str) -> Optional[Dict[str, Any]]:
        """Process a single video file with all analysis types."""
        video_name = video_uri.split('/')[-1]
        logger.info(f"Processing video: {video_name}")

        video_id = self._generate_video_id(video_uri)

        # Start parallel analysis operations
        logger.debug(f"Starting video analysis...")
        operations = self._start_video_analysis(video_uri)

        # Wait for operations to complete and collect results
        logger.debug(f"Waiting for analysis to complete...")
        analysis_results = self._wait_for_analysis(operations)

        # Process analysis results
        segments = self._process_shot_detection(analysis_results.get('shots', []), video_id, video_uri)
        transcripts = self._process_speech_transcription(analysis_results.get('speech', []), video_id, video_uri)

        if self.enable_ocr:
            ocr_results = self._process_text_detection(analysis_results.get('text', []), video_id, video_uri)
        else:
            ocr_results = []

        labels = analysis_results.get('labels', [])

        # Generate embeddings for segments
        self._generate_segment_embeddings(segments, video_id)

        # Store video metadata
        self._store_video_metadata(video_id, video_uri, segments, labels, analysis_results)

        # Update search corpus
        self._update_search_corpus(video_id, video_uri, segments, transcripts, ocr_results)

        return {
            'video_id': video_id,
            'uri': video_uri,
            'duration': analysis_results.get('duration', 0),
            'segments': len(segments),
            'transcripts': len(transcripts),
            'ocr_detections': len(ocr_results)
        }

    def _generate_video_id(self, video_uri: str) -> str:
        """Generate unique ID for video."""
        import hashlib
        return hashlib.md5(video_uri.encode()).hexdigest()

    def _start_video_analysis(self, video_uri: str) -> Dict[str, Any]:
        """Start parallel video analysis operations."""
        logger.info(f"Starting video analysis for {video_uri}")

        operations = {}

        # Configure video context with sampling
        video_context = videointelligence_v1.VideoContext(
            speech_transcription_config=videointelligence_v1.SpeechTranscriptionConfig(
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                enable_speaker_diarization=True,
                diarization_speaker_count=4,
                max_alternatives=1,  # Only get best alternative to save processing
            ),
            text_detection_config=videointelligence_v1.TextDetectionConfig(
                language_hints=["en"],
                model="builtin/latest",  # Use latest model
            ),
            # Add segment configuration for sampling
            segments=[
                videointelligence_v1.VideoSegment(
                    start_time_offset={'seconds': 0},
                    end_time_offset={'seconds': 120}  # Process only first 2 minutes by default
                )
            ] if self.segment_sample_interval > 0 else None
        )

        # Shot detection
        try:
            shot_operation = self.video_client.annotate_video(
                request={
                    "input_uri": video_uri,
                    "features": [videointelligence_v1.Feature.SHOT_CHANGE_DETECTION],
                }
            )
            operations['shots'] = shot_operation
            logger.info("Started shot detection")
        except Exception as e:
            logger.error(f"Failed to start shot detection: {e}")

        # Speech transcription
        try:
            speech_operation = self.video_client.annotate_video(
                request={
                    "input_uri": video_uri,
                    "features": [videointelligence_v1.Feature.SPEECH_TRANSCRIPTION],
                    "video_context": video_context,
                }
            )
            operations['speech'] = speech_operation
            logger.info("Started speech transcription")
        except Exception as e:
            logger.error(f"Failed to start speech transcription: {e}")

        # Text detection (OCR) - only if enabled
        if self.enable_ocr:
            try:
                text_operation = self.video_client.annotate_video(
                    request={
                        "input_uri": video_uri,
                        "features": [videointelligence_v1.Feature.TEXT_DETECTION],
                        "video_context": video_context,
                    }
                )
                operations['text'] = text_operation
                logger.info("Started text detection")
            except Exception as e:
                logger.error(f"Failed to start text detection: {e}")
        else:
            logger.info("OCR disabled for video processing (saves costs)")

        # Label detection - only if enabled
        if self.enable_labels:
            try:
                label_operation = self.video_client.annotate_video(
                    request={
                        "input_uri": video_uri,
                        "features": [
                            videointelligence_v1.Feature.LABEL_DETECTION,
                        ],
                    }
                )
                operations['labels'] = label_operation
                logger.info("Started label detection")
            except Exception as e:
                logger.error(f"Failed to start label detection: {e}")
        else:
            logger.info("Label detection disabled for video processing (saves costs)")

        return operations

    def _wait_for_analysis(self, operations: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
        """Wait for all analysis operations to complete."""
        results = {}

        for name, operation in operations.items():
            try:
                logger.info(f"Waiting for {name} analysis to complete...")
                result = operation.result(timeout=timeout)

                if name == 'shots' and result.annotation_results:
                    results['shots'] = result.annotation_results[0].shot_annotations
                    results['duration'] = result.annotation_results[0].segment.end_time_offset.total_seconds()

                elif name == 'speech' and result.annotation_results:
                    results['speech'] = result.annotation_results[0].speech_transcriptions

                elif name == 'text' and result.annotation_results:
                    results['text'] = result.annotation_results[0].text_annotations

                elif name == 'labels' and result.annotation_results:
                    results['labels'] = result.annotation_results[0].segment_label_annotations

                logger.info(f"{name} analysis completed")

            except Exception as e:
                logger.error(f"Failed to get {name} results: {e}")

        return results

    def _process_shot_detection(self, shots: List[Any], video_id: str, video_uri: str) -> List[VideoSegment]:
        """Process shot detection results into segments."""
        segments = []

        # Apply sampling to reduce segments if interval is set
        if self.segment_sample_interval > 0:
            # Group shots by time intervals
            sampled_shots = []
            last_sample_time = -self.segment_sample_interval

            for shot in shots:
                start_time = shot.start_time_offset.total_seconds() if shot.start_time_offset else 0

                # Take one shot per interval
                if start_time >= last_sample_time + self.segment_sample_interval:
                    sampled_shots.append(shot)
                    last_sample_time = start_time

            logger.info(f"Sampled {len(sampled_shots)} shots from {len(shots)} total (interval: {self.segment_sample_interval}s)")
            shots = sampled_shots

        for i, shot in enumerate(shots):
            start_time = shot.start_time_offset.total_seconds() if shot.start_time_offset else 0
            end_time = shot.end_time_offset.total_seconds() if shot.end_time_offset else 0
            duration = end_time - start_time

            # Skip very short segments
            if duration < self.min_segment_duration:
                continue

            # For sampled mode, don't split long segments
            if self.segment_sample_interval > 0:
                # Keep segments as-is when sampling
                segment = VideoSegment(
                    segment_id=f"{video_id}_shot_{i}",
                    start_time=start_time,
                    end_time=min(end_time, start_time + self.max_segment_duration),
                    duration=min(duration, self.max_segment_duration),
                    shot_label=f"shot_{i}",
                    confidence=0.95
                )
                segments.append(segment)
            else:
                # Split very long segments only in full mode
                if duration > self.max_segment_duration:
                    num_splits = int(duration / self.max_segment_duration) + 1
                    split_duration = duration / num_splits

                    for j in range(num_splits):
                        segment = VideoSegment(
                            segment_id=f"{video_id}_shot_{i}_{j}",
                            start_time=start_time + (j * split_duration),
                            end_time=start_time + ((j + 1) * split_duration),
                            duration=split_duration,
                            shot_label=f"shot_{i}_part_{j}",
                            confidence=0.95
                        )
                        segments.append(segment)
                else:
                    segment = VideoSegment(
                        segment_id=f"{video_id}_shot_{i}",
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        shot_label=f"shot_{i}",
                        confidence=0.95
                    )
                    segments.append(segment)

        # Store segments in database
        self._store_segments(segments, video_id, video_uri)

        logger.info(f"Processed {len(segments)} video segments")
        return segments

    def _process_speech_transcription(self, transcriptions: List[Any], video_id: str, video_uri: str) -> List[Dict]:
        """Process speech transcription results."""
        transcripts = []

        for transcription in transcriptions:
            for alternative in transcription.alternatives:
                transcript_text = alternative.transcript
                confidence = alternative.confidence if hasattr(alternative, 'confidence') else 0.95

                # Extract word timestamps
                word_timestamps = []
                if hasattr(alternative, 'words'):
                    for word in alternative.words:
                        # Video Intelligence API uses start_time/end_time, not start_offset/end_offset
                        start_time = 0
                        end_time = 0
                        if hasattr(word, 'start_time'):
                            start_time = word.start_time.total_seconds() if word.start_time else 0
                        elif hasattr(word, 'start_offset'):
                            start_time = word.start_offset.total_seconds() if word.start_offset else 0

                        if hasattr(word, 'end_time'):
                            end_time = word.end_time.total_seconds() if word.end_time else 0
                        elif hasattr(word, 'end_offset'):
                            end_time = word.end_offset.total_seconds() if word.end_offset else 0

                        word_timestamps.append({
                            'word': word.word,
                            'start_time': start_time,
                            'end_time': end_time,
                            'confidence': word.confidence if hasattr(word, 'confidence') else confidence,
                            'speaker_tag': word.speaker_tag if hasattr(word, 'speaker_tag') else 0
                        })

                # Group by speaker segments
                speaker_segments = self._group_by_speaker(word_timestamps)

                for segment in speaker_segments:
                    transcript = {
                        'transcript_id': f"{video_id}_transcript_{len(transcripts)}",
                        'video_id': video_id,
                        'uri': video_uri,
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'speaker_id': str(segment['speaker_id']),
                        'text': segment['text'],
                        'confidence': segment['confidence'],
                        'word_timestamps': segment.get('words', [])
                    }
                    transcripts.append(transcript)

        # Store transcripts
        self._store_transcripts(transcripts)

        logger.info(f"Processed {len(transcripts)} transcript segments")
        return transcripts

    def _process_text_detection(self, text_annotations: List[Any], video_id: str, video_uri: str) -> List[Dict]:
        """Process OCR text detection results."""
        ocr_results = []

        for annotation in text_annotations:
            text = annotation.text

            for segment in annotation.segments:
                start_time = segment.segment.start_time_offset.total_seconds() if segment.segment.start_time_offset else 0
                end_time = segment.segment.end_time_offset.total_seconds() if segment.segment.end_time_offset else 0
                confidence = segment.confidence

                # Get bounding box from first frame
                bounding_box = None
                if segment.frames:
                    frame = segment.frames[0]
                    if frame.rotated_bounding_box and frame.rotated_bounding_box.vertices:
                        vertices = frame.rotated_bounding_box.vertices
                        bounding_box = {
                            'left_x': min(v.x for v in vertices),
                            'top_y': min(v.y for v in vertices),
                            'right_x': max(v.x for v in vertices),
                            'bottom_y': max(v.y for v in vertices)
                        }

                ocr_result = {
                    'ocr_id': f"{video_id}_ocr_{len(ocr_results)}",
                    'video_id': video_id,
                    'uri': video_uri,
                    'frame_time': (start_time + end_time) / 2,  # Use middle of segment
                    'text': text,
                    'confidence': confidence,
                    'bounding_box': bounding_box
                }
                ocr_results.append(ocr_result)

        # Store OCR results
        self._store_ocr_results(ocr_results)

        logger.info(f"Processed {len(ocr_results)} OCR detections")
        return ocr_results

    def _group_by_speaker(self, word_timestamps: List[Dict]) -> List[Dict]:
        """Group word timestamps by speaker."""
        if not word_timestamps:
            return []

        segments = []
        current_segment = {
            'speaker_id': word_timestamps[0].get('speaker_tag', 0),
            'start_time': word_timestamps[0]['start_time'],
            'end_time': word_timestamps[0]['end_time'],
            'words': [word_timestamps[0]],
            'confidence': word_timestamps[0].get('confidence', 0.95)
        }

        for word in word_timestamps[1:]:
            speaker = word.get('speaker_tag', 0)
            if speaker == current_segment['speaker_id']:
                current_segment['words'].append(word)
                current_segment['end_time'] = word['end_time']
            else:
                # Finalize current segment
                current_segment['text'] = ' '.join(w['word'] for w in current_segment['words'])
                segments.append(current_segment)

                # Start new segment
                current_segment = {
                    'speaker_id': speaker,
                    'start_time': word['start_time'],
                    'end_time': word['end_time'],
                    'words': [word],
                    'confidence': word.get('confidence', 0.95)
                }

        # Add last segment
        if current_segment:
            current_segment['text'] = ' '.join(w['word'] for w in current_segment['words'])
            segments.append(current_segment)

        return segments

    def _generate_segment_embeddings(self, segments: List[VideoSegment], video_id: str) -> None:
        """Generate multimodal embeddings for video segments."""
        logger.info(f"Generating embeddings for {len(segments)} segments")

        # For now, we'll generate text-based embeddings from metadata
        # In production, you'd extract key frames and use multimodal embeddings

        from google.cloud import aiplatform

        # Initialize the embedding model
        embedding_model = "text-embedding-004"

        for segment in segments:
            # Create text description of segment for embedding
            segment_text = f"Video segment from {segment.start_time:.1f}s to {segment.end_time:.1f}s"
            if segment.transcript_text:
                segment_text += f" Transcript: {segment.transcript_text}"
            if segment.ocr_text:
                segment_text += f" On-screen text: {segment.ocr_text}"

            try:
                # Generate embedding using Vertex AI
                vertex_location = getattr(self.config, 'vertex_location', self.config.location)
                if vertex_location == 'US':
                    vertex_location = 'us-central1'
                embeddings = aiplatform.gapic.PredictionServiceClient(
                    client_options={"api_endpoint": f"{vertex_location}-aiplatform.googleapis.com"}
                )

                instances = [{"content": segment_text}]

                response = embeddings.predict(
                    endpoint=f"projects/{self.config.project_id}/locations/{vertex_location}/publishers/google/models/{embedding_model}",
                    instances=instances,
                )

                if response.predictions:
                    segment.visual_embedding = response.predictions[0]['embeddings']['values']

            except Exception as e:
                logger.error(f"Failed to generate embedding for segment {segment.segment_id}: {e}")

    def _store_segments(self, segments: List[VideoSegment], video_id: str, video_uri: str) -> None:
        """Store video segments in database."""
        from google.cloud import bigquery

        for i, segment in enumerate(segments):
            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.video_segments`
            (segment_id, video_id, uri, segment_index, start_time, end_time, duration,
             shot_label, confidence, visual_embedding, embedding_model, metadata)
            VALUES (
                @segment_id,
                @video_id,
                @uri,
                @segment_index,
                @start_time,
                @end_time,
                @duration,
                @shot_label,
                @confidence,
                @visual_embedding,
                @embedding_model,
                @metadata
            )
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter('segment_id', 'STRING', segment.segment_id),
                    bigquery.ScalarQueryParameter('video_id', 'STRING', video_id),
                    bigquery.ScalarQueryParameter('uri', 'STRING', video_uri),
                    bigquery.ScalarQueryParameter('segment_index', 'INT64', i),
                    bigquery.ScalarQueryParameter('start_time', 'FLOAT64', segment.start_time),
                    bigquery.ScalarQueryParameter('end_time', 'FLOAT64', segment.end_time),
                    bigquery.ScalarQueryParameter('duration', 'FLOAT64', segment.duration),
                    bigquery.ScalarQueryParameter('shot_label', 'STRING', segment.shot_label or ''),
                    bigquery.ScalarQueryParameter('confidence', 'FLOAT64', segment.confidence),
                    bigquery.ArrayQueryParameter('visual_embedding', 'FLOAT64', segment.visual_embedding or []),
                    bigquery.ScalarQueryParameter('embedding_model', 'STRING', 'text-embedding-004'),
                    bigquery.ScalarQueryParameter('metadata', 'JSON', json.dumps(segment.metadata or {}))
                ]
            )

            try:
                self.client.client.query(query, job_config=job_config).result()
            except Exception as e:
                logger.error(f"Failed to store segment {segment.segment_id}: {e}")

    def _store_transcripts(self, transcripts: List[Dict]) -> None:
        """Store video transcripts in database."""
        from google.cloud import bigquery

        for transcript in transcripts:
            # Generate text embedding for transcript
            text_embedding = self._generate_text_embedding(transcript['text'])

            query = f"""
            INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.video_transcripts`
            (transcript_id, video_id, uri, start_time, end_time, speaker_id, text,
             confidence, text_embedding)
            VALUES (
                @transcript_id,
                @video_id,
                @uri,
                @start_time,
                @end_time,
                @speaker_id,
                @text,
                @confidence,
                @text_embedding
            )
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter('transcript_id', 'STRING', transcript['transcript_id']),
                    bigquery.ScalarQueryParameter('video_id', 'STRING', transcript['video_id']),
                    bigquery.ScalarQueryParameter('uri', 'STRING', transcript['uri']),
                    bigquery.ScalarQueryParameter('start_time', 'FLOAT64', transcript['start_time']),
                    bigquery.ScalarQueryParameter('end_time', 'FLOAT64', transcript['end_time']),
                    bigquery.ScalarQueryParameter('speaker_id', 'STRING', transcript.get('speaker_id', '0')),
                    bigquery.ScalarQueryParameter('text', 'STRING', transcript['text']),
                    bigquery.ScalarQueryParameter('confidence', 'FLOAT64', transcript['confidence']),
                    bigquery.ArrayQueryParameter('text_embedding', 'FLOAT64', text_embedding or [])
                ]
            )

            try:
                self.client.client.query(query, job_config=job_config).result()
            except Exception as e:
                logger.error(f"Failed to store transcript {transcript['transcript_id']}: {e}")

    def _store_ocr_results(self, ocr_results: List[Dict]) -> None:
        """Store OCR results in database."""
        from google.cloud import bigquery

        for ocr in ocr_results:
            # Generate text embedding for OCR text
            text_embedding = self._generate_text_embedding(ocr['text'])

            # Handle bounding box - either use STRUCT or NULL
            bbox = ocr.get('bounding_box')
            if bbox and all(k in bbox for k in ['left_x', 'top_y', 'right_x', 'bottom_y']):
                query = f"""
                INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.video_ocr_text`
                (ocr_id, video_id, uri, frame_time, text, confidence, bounding_box, text_embedding)
                VALUES (
                    @ocr_id,
                    @video_id,
                    @uri,
                    @frame_time,
                    @text,
                    @confidence,
                    STRUCT(
                        @left_x AS left_x,
                        @top_y AS top_y,
                        @right_x AS right_x,
                        @bottom_y AS bottom_y
                    ),
                    @text_embedding
                )
                """

                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter('ocr_id', 'STRING', ocr['ocr_id']),
                        bigquery.ScalarQueryParameter('video_id', 'STRING', ocr['video_id']),
                        bigquery.ScalarQueryParameter('uri', 'STRING', ocr['uri']),
                        bigquery.ScalarQueryParameter('frame_time', 'FLOAT64', ocr['frame_time']),
                        bigquery.ScalarQueryParameter('text', 'STRING', ocr['text']),
                        bigquery.ScalarQueryParameter('confidence', 'FLOAT64', ocr['confidence']),
                        bigquery.ScalarQueryParameter('left_x', 'FLOAT64', bbox['left_x']),
                        bigquery.ScalarQueryParameter('top_y', 'FLOAT64', bbox['top_y']),
                        bigquery.ScalarQueryParameter('right_x', 'FLOAT64', bbox['right_x']),
                        bigquery.ScalarQueryParameter('bottom_y', 'FLOAT64', bbox['bottom_y']),
                        bigquery.ArrayQueryParameter('text_embedding', 'FLOAT64', text_embedding or [])
                    ]
                )
            else:
                # Insert without bounding box
                query = f"""
                INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.video_ocr_text`
                (ocr_id, video_id, uri, frame_time, text, confidence, text_embedding)
                VALUES (
                    @ocr_id,
                    @video_id,
                    @uri,
                    @frame_time,
                    @text,
                    @confidence,
                    @text_embedding
                )
                """

                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter('ocr_id', 'STRING', ocr['ocr_id']),
                        bigquery.ScalarQueryParameter('video_id', 'STRING', ocr['video_id']),
                        bigquery.ScalarQueryParameter('uri', 'STRING', ocr['uri']),
                        bigquery.ScalarQueryParameter('frame_time', 'FLOAT64', ocr['frame_time']),
                        bigquery.ScalarQueryParameter('text', 'STRING', ocr['text']),
                        bigquery.ScalarQueryParameter('confidence', 'FLOAT64', ocr['confidence']),
                        bigquery.ArrayQueryParameter('text_embedding', 'FLOAT64', text_embedding or [])
                    ]
                )

            try:
                self.client.client.query(query, job_config=job_config).result()
            except Exception as e:
                logger.error(f"Failed to store OCR result {ocr['ocr_id']}: {e}")

    def _generate_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text embedding using Vertex AI."""
        if not text:
            return None

        try:
            from google.cloud import aiplatform

            vertex_location = getattr(self.config, 'vertex_location', self.config.location)
            if vertex_location == 'US':
                vertex_location = 'us-central1'
            embeddings = aiplatform.gapic.PredictionServiceClient(
                client_options={"api_endpoint": f"{vertex_location}-aiplatform.googleapis.com"}
            )

            instances = [{"content": text[:2000]}]  # Limit text length

            response = embeddings.predict(
                endpoint=f"projects/{self.config.project_id}/locations/{vertex_location}/publishers/google/models/text-embedding-004",
                instances=instances,
            )

            if response.predictions:
                return response.predictions[0]['embeddings']['values']

        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")

        return None

    def _store_video_metadata(self, video_id: str, video_uri: str, segments: List[VideoSegment],
                             labels: List[Any], analysis_results: Dict) -> None:
        """Store video metadata."""
        from google.cloud import bigquery

        # Extract shot change timestamps
        shot_changes = [segment.start_time for segment in segments]

        processing_metadata = {
            'processed_at': datetime.utcnow().isoformat(),
            'segment_count': len(segments),
            'features': ['shot_detection', 'speech_transcription', 'text_detection', 'label_detection']
        }

        # For now, skip labels to avoid complex STRUCT issues
        # We can add them later with proper STRUCT formatting
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.video_metadata`
        (video_id, uri, duration_seconds, segment_count, shot_changes, processing_metadata)
        VALUES (
            @video_id,
            @uri,
            @duration,
            @segment_count,
            @shot_changes,
            @processing_metadata
        )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter('video_id', 'STRING', video_id),
                bigquery.ScalarQueryParameter('uri', 'STRING', video_uri),
                bigquery.ScalarQueryParameter('duration', 'FLOAT64', analysis_results.get('duration', 0)),
                bigquery.ScalarQueryParameter('segment_count', 'INT64', len(segments)),
                bigquery.ArrayQueryParameter('shot_changes', 'FLOAT64', shot_changes),
                bigquery.ScalarQueryParameter('processing_metadata', 'JSON', json.dumps(processing_metadata))
            ]
        )

        try:
            self.client.client.query(query, job_config=job_config).result()
            logger.info(f"Stored metadata for video {video_id}")
        except Exception as e:
            logger.error(f"Failed to store video metadata: {e}")

    def _update_search_corpus(self, video_id: str, video_uri: str, segments: List[VideoSegment],
                             transcripts: List[Dict], ocr_results: List[Dict]) -> None:
        """Update search corpus with video content."""
        logger.info("Updating search corpus with video content...")

        # Create searchable content
        filename = video_uri.split('/')[-1]
        content_parts = [
            f"Video File: {filename}",
            f"Segments: {len(segments)}",
            ""
        ]

        # Add transcript summary
        if transcripts:
            content_parts.append("Transcript excerpts:")
            for t in transcripts[:3]:  # First 3 segments
                content_parts.append(f"  [{t.get('speaker_id', 'Speaker')}]: {t['text'][:100]}...")
            content_parts.append("")

        # Add OCR text summary
        if ocr_results:
            content_parts.append("On-screen text detected:")
            unique_texts = list(set(ocr['text'] for ocr in ocr_results[:5]))
            for text in unique_texts:
                content_parts.append(f"  - {text[:50]}")
            content_parts.append("")

        content_parts.append(f"Indexed: {datetime.utcnow().isoformat()}")
        full_content = '\n'.join(content_parts)

        # Insert into documents table
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        (doc_id, uri, modality, source, created_at, text_content, meta)
        VALUES (
            @doc_id,
            @uri,
            'video',
            'video',
            CURRENT_TIMESTAMP(),
            @text_content,
            @meta
        )
        """

        meta_data = {
            'video_id': video_id,
            'segment_count': len(segments),
            'transcript_count': len(transcripts),
            'ocr_count': len(ocr_results)
        }

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter('doc_id', 'STRING', video_id),
                bigquery.ScalarQueryParameter('uri', 'STRING', video_uri),
                bigquery.ScalarQueryParameter('text_content', 'STRING', full_content),
                bigquery.ScalarQueryParameter('meta', 'JSON', json.dumps(meta_data))
            ]
        )

        try:
            self.client.client.query(query, job_config=job_config).result()
            logger.info(f"Added video {video_id} to search corpus")
        except Exception as e:
            logger.error(f"Failed to update search corpus: {e}")

    def search_videos(self, query: str, search_type: str = 'hybrid', top_k: int = 10) -> List[Dict]:
        """
        Search videos using different strategies.

        Args:
            query: Search query
            search_type: 'transcript', 'ocr', 'visual', or 'hybrid'
            top_k: Number of results to return

        Returns:
            List of search results with timestamps
        """
        results = []

        if search_type in ['transcript', 'hybrid']:
            transcript_results = self._search_transcripts(query, top_k)
            results.extend(transcript_results)

        if search_type in ['ocr', 'hybrid']:
            ocr_results = self._search_ocr(query, top_k)
            results.extend(ocr_results)

        if search_type in ['visual', 'hybrid']:
            visual_results = self._search_visual(query, top_k)
            results.extend(visual_results)

        # Deduplicate and rank results
        seen_segments = set()
        unique_results = []

        for result in sorted(results, key=lambda x: x.get('score', 0), reverse=True):
            segment_key = (result['video_id'], result.get('start_time', 0))
            if segment_key not in seen_segments:
                seen_segments.add(segment_key)
                unique_results.append(result)
                if len(unique_results) >= top_k:
                    break

        return unique_results

    def _search_transcripts(self, query: str, top_k: int) -> List[Dict]:
        """Search video transcripts."""
        # Generate query embedding
        query_embedding = self._generate_text_embedding(query)

        if not query_embedding:
            return []

        # Vector similarity search on transcripts
        query_sql = f"""
        WITH query_embedding AS (
            SELECT {query_embedding} AS embedding
        )
        SELECT
            t.video_id,
            t.uri,
            t.start_time,
            t.end_time,
            t.text,
            t.speaker_id,
            ML.DISTANCE(t.text_embedding, q.embedding, 'COSINE') AS distance,
            1 - ML.DISTANCE(t.text_embedding, q.embedding, 'COSINE') AS score
        FROM `{self.config.project_id}.{self.config.dataset_name}.video_transcripts` t
        CROSS JOIN query_embedding q
        WHERE ARRAY_LENGTH(t.text_embedding) > 0
        ORDER BY distance
        LIMIT {top_k}
        """

        try:
            results = self.client.execute_query_and_wait(query_sql)
            return [
                {
                    'video_id': row['video_id'],
                    'uri': row['uri'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'text': row['text'],
                    'speaker_id': row['speaker_id'],
                    'score': row['score'],
                    'result_type': 'transcript'
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Transcript search failed: {e}")
            return []

    def _search_ocr(self, query: str, top_k: int) -> List[Dict]:
        """Search OCR text from videos."""
        # Generate query embedding
        query_embedding = self._generate_text_embedding(query)

        if not query_embedding:
            return []

        # Vector similarity search on OCR text
        query_sql = f"""
        WITH query_embedding AS (
            SELECT {query_embedding} AS embedding
        )
        SELECT
            o.video_id,
            o.uri,
            o.frame_time,
            o.text,
            ML.DISTANCE(o.text_embedding, q.embedding, 'COSINE') AS distance,
            1 - ML.DISTANCE(o.text_embedding, q.embedding, 'COSINE') AS score
        FROM `{self.config.project_id}.{self.config.dataset_name}.video_ocr_text` o
        CROSS JOIN query_embedding q
        WHERE ARRAY_LENGTH(o.text_embedding) > 0
        ORDER BY distance
        LIMIT {top_k}
        """

        try:
            results = self.client.execute_query_and_wait(query_sql)
            return [
                {
                    'video_id': row['video_id'],
                    'uri': row['uri'],
                    'start_time': row['frame_time'],
                    'end_time': row['frame_time'] + 1,  # Assume 1 second for frame
                    'text': row['text'],
                    'score': row['score'],
                    'result_type': 'ocr'
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"OCR search failed: {e}")
            return []

    def _search_visual(self, query: str, top_k: int) -> List[Dict]:
        """Search video segments using visual embeddings."""
        # Generate query embedding (cross-modal)
        query_embedding = self._generate_text_embedding(query)

        if not query_embedding:
            return []

        # Vector similarity search on visual segments
        query_sql = f"""
        WITH query_embedding AS (
            SELECT {query_embedding} AS embedding
        )
        SELECT
            s.video_id,
            s.uri,
            s.start_time,
            s.end_time,
            s.shot_label,
            ML.DISTANCE(s.visual_embedding, q.embedding, 'COSINE') AS distance,
            1 - ML.DISTANCE(s.visual_embedding, q.embedding, 'COSINE') AS score
        FROM `{self.config.project_id}.{self.config.dataset_name}.video_segments` s
        CROSS JOIN query_embedding q
        WHERE ARRAY_LENGTH(s.visual_embedding) > 0
        ORDER BY distance
        LIMIT {top_k}
        """

        try:
            results = self.client.execute_query_and_wait(query_sql)
            return [
                {
                    'video_id': row['video_id'],
                    'uri': row['uri'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'shot_label': row['shot_label'],
                    'score': row['score'],
                    'result_type': 'visual'
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Visual search failed: {e}")
            return []
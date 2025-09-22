"""
Text extraction from various file formats using BigQuery ML.
"""

import logging
from typing import Dict, Any, Optional

from ..config import Config
from ..bigquery.connection import BigQueryClient
from ..bigquery.queries import QueryTemplates


logger = logging.getLogger(__name__)


class TextExtractor:
    """Extract text from various file formats using BigQuery ML."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize text extractor."""
        self.client = client
        self.config = config
        self.queries = QueryTemplates()

    def extract_pdf_text(self) -> int:
        """Extract text from PDF files."""
        # This method is deprecated - PDFs are now handled by PDFProcessor
        logger.debug("PDF processing is now handled by PDFProcessor class")
        return 0

    def extract_image_text(self) -> int:
        """Perform OCR on images."""
        # This method is deprecated - Images are now handled by ImageProcessor
        logger.debug("Image processing is now handled by ImageProcessor class")
        return 0

    def extract_audio_text(self) -> int:
        """Transcribe audio files using AudioProcessor."""
        logger.info("Processing audio files with Speech-to-Text API...")

        from .audio_processor import AudioProcessor

        audio_processor = AudioProcessor(self.client, self.config)

        # Create audio metadata table if needed
        audio_processor.create_audio_metadata_table()

        # Process audio files
        stats = audio_processor.process_audio_files(batch_size=10)

        # Update search corpus
        corpus_count = audio_processor.update_search_corpus()
        logger.info(f"Added {corpus_count} audio documents to search corpus")

        return stats.get('files_processed', 0)

    def extract_video_text(self) -> int:
        """Transcribe video files."""
        logger.warning("Video transcription requires ML.GENERATE_TEXT which is not available.")
        logger.info("Please use alternative methods:")
        logger.info("  1. Pre-process videos using Video Intelligence API")
        logger.info("  2. Use Cloud Functions with Video Intelligence API")
        logger.info("  3. Extract transcripts before ingestion")
        return 0

    def ingest_text_files(self) -> int:
        """Ingest plain text files directly."""
        logger.info("Ingesting text files...")

        query = self.queries.ingest_text_files(
            self.config.project_id,
            self.config.dataset_name
        )

        try:
            job = self.client.execute_query(query)
            logger.info("Query submitted, waiting for completion...")
            job.result(timeout=300)  # 5 minute timeout
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Ingested {num_rows} text files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to ingest text files: {e}")
            return 0

    def ingest_markdown_files(self) -> int:
        """Ingest markdown files directly."""
        logger.info("Ingesting markdown files...")

        query = self.queries.ingest_markdown_files(
            self.config.project_id,
            self.config.dataset_name
        )

        try:
            job = self.client.execute_query(query)
            logger.info("Query submitted, waiting for completion...")
            job.result(timeout=300)  # 5 minute timeout
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Ingested {num_rows} markdown files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to ingest markdown files: {e}")
            return 0

    def summarize_json_files(self) -> int:
        """Process JSON files for searchability."""
        logger.info("Processing JSON files...")

        # Use direct JSON parsing instead of ML.GENERATE_TEXT
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'json' AS modality,
            'json' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            NULL AS author,
            NULL AS channel,
            -- Convert JSON to searchable text format
            TO_JSON_STRING(PARSE_JSON(SAFE_CONVERT_BYTES_TO_STRING(data))) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            NULL AS chunk_index,
            NULL AS chunk_start,
            NULL AS chunk_end,
            NULL AS embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_json`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            WHERE modality = 'json'
        )
        """

        try:
            job = self.client.execute_query(query)
            logger.info("Query submitted, waiting for completion...")
            job.result(timeout=300)  # 5 minute timeout
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Processed {num_rows} JSON files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to process JSON files: {e}")
            return 0

    def summarize_csv_files(self) -> int:
        """Process CSV files for searchability."""
        logger.info("Processing CSV files...")

        # Convert CSV data to searchable text format without ML.GENERATE_TEXT
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'csv' AS modality,
            'csv' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            NULL AS author,
            NULL AS channel,
            -- Convert CSV to searchable text
            SAFE_CONVERT_BYTES_TO_STRING(data) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            NULL AS chunk_index,
            NULL AS chunk_start,
            NULL AS chunk_end,
            NULL AS embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_csv`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            WHERE modality = 'csv'
        )
        """

        try:
            job = self.client.execute_query(query)
            logger.info("Query submitted, waiting for completion...")
            job.result(timeout=300)  # 5 minute timeout
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Processed {num_rows} CSV files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to process CSV files: {e}")
            return 0

    def extract_document_text(self) -> int:
        """Extract text from office documents (doc, docx, etc.)."""
        logger.info("Extracting text from office documents...")

        # Similar to PDF extraction but for office documents
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'document' AS modality,
            'document' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            NULL AS author,
            NULL AS channel,
            SAFE_CONVERT_BYTES_TO_STRING(data) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            NULL AS chunk_index,
            NULL AS chunk_start,
            NULL AS chunk_end,
            NULL AS embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_documents`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            WHERE modality = 'document'
        )
        """

        try:
            job = self.client.execute_query(query)
            logger.info("Query submitted, waiting for completion...")
            job.result(timeout=300)  # 5 minute timeout
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Extracted text from {num_rows} office documents")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to extract document text: {e}")
            return 0

    def extract_all(self) -> Dict[str, int]:
        """Extract text from all supported formats."""
        results = {
            'pdf': self.extract_pdf_text(),
            'images': self.extract_image_text(),
            'audio': self.extract_audio_text(),
            'video': self.extract_video_text(),
            'text': self.ingest_text_files(),
            'markdown': self.ingest_markdown_files(),
            'json': self.summarize_json_files(),
            'csv': self.summarize_csv_files(),
            'documents': self.extract_document_text()
        }

        total = sum(results.values())
        logger.info(f"Total documents processed: {total}")

        return results
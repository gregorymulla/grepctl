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
        """Extract text from PDF files using ML.GENERATE_TEXT."""
        logger.info("Extracting text from PDF files...")

        query = self.queries.extract_text_from_pdf(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()  # Wait for completion
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Extracted text from {num_rows} PDF files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return 0

    def extract_image_text(self) -> int:
        """Perform OCR on images using ML.GENERATE_TEXT."""
        logger.info("Performing OCR on images...")

        query = self.queries.extract_text_from_images(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Extracted text from {num_rows} images")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to extract image text: {e}")
            return 0

    def extract_audio_text(self) -> int:
        """Transcribe audio files using ML.GENERATE_TEXT."""
        logger.info("Transcribing audio files...")

        query = self.queries.extract_text_from_audio(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Transcribed {num_rows} audio files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            return 0

    def extract_video_text(self) -> int:
        """Transcribe video files using ML.GENERATE_TEXT."""
        logger.info("Transcribing video files...")

        query = self.queries.extract_text_from_video(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Transcribed {num_rows} video files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to transcribe video: {e}")
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
            job.result()
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
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Ingested {num_rows} markdown files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to ingest markdown files: {e}")
            return 0

    def summarize_json_files(self) -> int:
        """Summarize JSON files for searchability."""
        logger.info("Summarizing JSON files...")

        query = self.queries.summarize_json_files(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Summarized {num_rows} JSON files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to summarize JSON files: {e}")
            return 0

    def summarize_csv_files(self) -> int:
        """Summarize CSV files for searchability."""
        logger.info("Summarizing CSV files...")

        query = self.queries.summarize_csv_files(
            self.config.project_id,
            self.config.dataset_name,
            self.config.text_model
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Summarized {num_rows} CSV files")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to summarize CSV files: {e}")
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
            ML.GENERATE_TEXT(
                MODEL `{self.config.text_model}`,
                CONCAT(
                    'Extract all text content from this document. ',
                    'Preserve structure and formatting. ',
                    'Output clean, readable text only.'
                ),
                data
            ).ml_generate_text_result AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation,
                metageneration
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
            job.result()
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
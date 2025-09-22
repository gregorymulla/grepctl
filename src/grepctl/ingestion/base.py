"""
Base ingestion pipeline for multimodal data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import Config
from ..bigquery.connection import BigQueryClient
from ..bigquery.queries import QueryTemplates
from .text_extractor import TextExtractor
from .chunking import DocumentChunker
from .embeddings import EmbeddingManager
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .video_processor import VideoProcessor


logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Main ingestion pipeline for multimodal data."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize ingestion pipeline."""
        self.client = client
        self.config = config
        self.queries = QueryTemplates()
        self.text_extractor = TextExtractor(client, config)
        self.chunker = DocumentChunker(client, config)
        self.embedding_manager = EmbeddingManager(client, config)
        self.pdf_processor = PDFProcessor(client, config)
        self.image_processor = ImageProcessor(client, config)
        self.video_processor = VideoProcessor(client, config)

    def run(self, modalities: Optional[List[str]] = None,
            batch_size: int = 100,
            generate_embeddings: bool = True) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.

        Args:
            modalities: List of modalities to process, or ['all'] for all
            batch_size: Batch size for processing
            generate_embeddings: Whether to generate embeddings after ingestion

        Returns:
            Statistics about the ingestion process
        """
        stats = {
            'start_time': datetime.now(),
            'modalities': {},
            'total_documents': 0,
            'total_chunks': 0,
            'total_embeddings': 0,
            'errors': []
        }

        # Determine which modalities to process
        if not modalities or 'all' in modalities:
            modalities = list(self.config.modality_extensions.keys())

        logger.info(f"Starting ingestion for modalities: {modalities}")

        # Process each modality
        for modality in modalities:
            try:
                modality_stats = self._process_modality(modality, batch_size)
                stats['modalities'][modality] = modality_stats
                stats['total_documents'] += modality_stats.get('documents', 0)
            except Exception as e:
                logger.error(f"Error processing {modality}: {e}")
                stats['errors'].append({'modality': modality, 'error': str(e)})

        # Skip chunking and search corpus creation for now
        # (These tables already exist with data)
        logger.info("Skipping chunking and search corpus creation (tables already exist)")

        # Generate embeddings
        if generate_embeddings:
            try:
                embedding_stats = self.embedding_manager.generate_all_embeddings(batch_size)
                stats['total_embeddings'] = embedding_stats['embeddings_generated']
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                stats['errors'].append({'step': 'embeddings', 'error': str(e)})

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Ingestion completed in {stats['duration']:.2f} seconds")
        logger.info(f"Total documents: {stats['total_documents']}")
        logger.info(f"Total chunks: {stats['total_chunks']}")
        logger.info(f"Total embeddings: {stats['total_embeddings']}")

        return stats

    def _process_modality(self, modality: str, batch_size: int) -> Dict[str, Any]:
        """Process a single modality."""
        logger.info(f"Processing {modality} files...")

        modality_stats = {
            'documents': 0,
            'errors': 0,
            'skipped': 0
        }

        try:
            # Extract text based on modality
            if modality == 'pdf':
                # Use the PDF processor instead of text_extractor
                logger.info("Processing PDFs with metadata-based approach...")
                # Setup and ingest PDFs
                self.pdf_processor.create_pdf_metadata_table()
                self.pdf_processor.add_sample_pdf_metadata()
                count = self.pdf_processor.ingest_pdfs_with_metadata()
                # Update search corpus
                self.pdf_processor.update_search_corpus()
            elif modality == 'images':
                # Use the Image processor instead of text_extractor
                logger.info("Processing images with description-based approach...")
                # Setup and ingest images
                self.image_processor.create_image_descriptions_table()
                self.image_processor.add_sample_descriptions()
                count = self.image_processor.ingest_images_with_descriptions()
                # Update search corpus
                self.image_processor.update_search_corpus()
            elif modality == 'audio':
                count = self.text_extractor.extract_audio_text()
            elif modality == 'video':
                # Use the Video processor instead of text_extractor
                logger.info("Processing videos with comprehensive analysis...")
                # Setup and process videos
                self.video_processor.create_video_tables()
                stats = self.video_processor.process_video_files(batch_size=batch_size)
                count = stats.get('files_processed', 0)
            elif modality == 'text':
                count = self.text_extractor.ingest_text_files()
            elif modality == 'markdown':
                count = self.text_extractor.ingest_markdown_files()
            elif modality == 'json':
                count = self.text_extractor.summarize_json_files()
            elif modality == 'csv':
                count = self.text_extractor.summarize_csv_files()
            elif modality == 'documents':
                count = self.text_extractor.extract_document_text()
            else:
                logger.warning(f"Unknown modality: {modality}")
                count = 0

            modality_stats['documents'] = count
            logger.info(f"Processed {count} {modality} files")

        except Exception as e:
            logger.error(f"Error processing {modality}: {e}")
            modality_stats['errors'] += 1

        return modality_stats

    def _create_search_corpus(self) -> None:
        """Create the unified search corpus."""
        logger.info("Creating search corpus...")

        query = self.queries.create_search_corpus(
            self.config.project_id,
            self.config.dataset_name,
            self.config.chunk_size
        )

        self.client.execute_query_and_wait(query)
        logger.info("Search corpus created successfully")

    def ingest_from_gcs(self, bucket: str, prefix: str,
                        modality: str, batch_size: int = 100) -> Dict[str, Any]:
        """
        Ingest data from a specific GCS location.

        Args:
            bucket: GCS bucket name
            prefix: Path prefix in the bucket
            modality: Type of data to ingest
            batch_size: Batch size for processing

        Returns:
            Ingestion statistics
        """
        # Update config temporarily
        original_bucket = self.config.gcs_bucket
        original_prefix = self.config.gcs_prefix

        self.config.gcs_bucket = bucket
        self.config.gcs_prefix = prefix

        try:
            stats = self.run([modality], batch_size)
        finally:
            # Restore original config
            self.config.gcs_bucket = original_bucket
            self.config.gcs_prefix = original_prefix

        return stats

    def validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met for ingestion."""
        checks = []

        # Check dataset exists
        if not self.client.check_dataset_exists():
            logger.error(f"Dataset {self.config.dataset_name} does not exist")
            checks.append(False)
        else:
            checks.append(True)

        # Check required tables exist
        required_tables = ['documents', 'document_chunks', 'search_corpus']
        for table in required_tables:
            if not self.client.table_exists(table):
                logger.error(f"Table {table} does not exist")
                checks.append(False)
            else:
                checks.append(True)

        # Check external tables exist (at least one)
        external_tables = [f"obj_{m}" for m in self.config.modality_extensions.keys()]
        external_exists = False
        for table in external_tables:
            if self.client.table_exists(table):
                external_exists = True
                break

        if not external_exists:
            logger.warning("No external tables found. Run setup first.")
            checks.append(False)
        else:
            checks.append(True)

        return all(checks)

    def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status and statistics."""
        status = {
            'documents': self.client.get_document_count(),
            'stats': self.client.get_document_stats(),
            'index': self.client.get_index_status(),
            'ready': self.validate_prerequisites()
        }

        return status
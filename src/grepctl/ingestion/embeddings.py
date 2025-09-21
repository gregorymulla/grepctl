"""
Embedding generation and vector index management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config import Config
from ..bigquery.connection import BigQueryClient
from ..bigquery.queries import QueryTemplates
from ..bigquery.schema import SchemaManager


logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manage embedding generation and vector index."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize embedding manager."""
        self.client = client
        self.config = config
        self.queries = QueryTemplates()
        self.schema_manager = SchemaManager(client, config)

    def generate_all_embeddings(self, batch_size: int = 100) -> Dict[str, Any]:
        """Generate embeddings for all documents without embeddings."""
        logger.info("Generating embeddings for documents...")

        stats = {
            'start_time': datetime.now(),
            'embeddings_generated': 0,
            'batches_processed': 0,
            'errors': 0
        }

        try:
            # Get count of documents needing embeddings
            count_query = f"""
            SELECT COUNT(*) as count
            FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
            AND text_content IS NOT NULL
            AND LENGTH(text_content) > 0
            """
            result = self.client.execute_query_and_wait(count_query)
            total_docs = result[0]['count'] if result else 0

            logger.info(f"Found {total_docs} documents needing embeddings")

            if total_docs == 0:
                logger.info("No documents need embeddings")
                return stats

            # Process in batches
            processed = 0
            while processed < total_docs:
                batch_stats = self._generate_batch_embeddings(batch_size)
                stats['batches_processed'] += 1
                stats['embeddings_generated'] += batch_stats['generated']

                if batch_stats['generated'] == 0:
                    # No more documents to process
                    break

                processed += batch_stats['generated']
                logger.info(f"Processed {processed}/{total_docs} documents")

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            stats['errors'] += 1

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Generated {stats['embeddings_generated']} embeddings in {stats['duration']:.2f} seconds")
        return stats

    def _generate_batch_embeddings(self, batch_size: int) -> Dict[str, Any]:
        """Generate embeddings for a batch of documents."""
        stats = {'generated': 0, 'errors': 0}

        query = self.queries.generate_embeddings(
            self.config.project_id,
            self.config.dataset_name,
            self.config.embedding_model,
            batch_size
        )

        try:
            job = self.client.execute_query(query)
            job.result()
            stats['generated'] = job.num_dml_affected_rows or 0
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            stats['errors'] += 1

        return stats

    def update_embeddings(self, force: bool = False) -> Dict[str, Any]:
        """Update embeddings for new or changed documents."""
        logger.info("Updating embeddings...")

        stats = {
            'new_embeddings': 0,
            'updated_embeddings': 0,
            'errors': 0
        }

        if force:
            # Clear all embeddings first
            clear_query = f"""
            UPDATE `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            SET embedding = NULL
            WHERE TRUE
            """
            try:
                self.client.execute_query_and_wait(clear_query)
                logger.info("Cleared all existing embeddings")
            except Exception as e:
                logger.error(f"Failed to clear embeddings: {e}")
                stats['errors'] += 1

        # Generate new embeddings
        gen_stats = self.generate_all_embeddings()
        stats['new_embeddings'] = gen_stats['embeddings_generated']

        return stats

    def rebuild_index(self) -> Dict[str, Any]:
        """Rebuild the vector index from scratch."""
        logger.info("Rebuilding vector index...")

        stats = {
            'start_time': datetime.now(),
            'documents_indexed': 0,
            'errors': 0
        }

        try:
            # First ensure all embeddings are generated
            embedding_stats = self.generate_all_embeddings()
            stats['documents_indexed'] = embedding_stats['embeddings_generated']

            # Then rebuild the index
            self.schema_manager.create_vector_index(rebuild=True)

            logger.info("Vector index rebuilt successfully")

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            stats['errors'] += 1

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        return stats

    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get statistics about embeddings."""
        query = f"""
        SELECT
            COUNT(*) as total_documents,
            COUNT(embedding) as documents_with_embeddings,
            COUNT(*) - COUNT(embedding) as documents_without_embeddings,
            AVG(ARRAY_LENGTH(embedding)) as avg_embedding_dimension
        FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        WHERE text_content IS NOT NULL
        """

        try:
            result = self.client.execute_query_and_wait(query)
            if result:
                stats = result[0]
                stats['coverage_percentage'] = (
                    stats['documents_with_embeddings'] / stats['total_documents'] * 100
                    if stats['total_documents'] > 0 else 0
                )
                return stats
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {e}")

        return {
            'total_documents': 0,
            'documents_with_embeddings': 0,
            'documents_without_embeddings': 0,
            'avg_embedding_dimension': 0,
            'coverage_percentage': 0
        }

    def validate_embeddings(self) -> Dict[str, Any]:
        """Validate embedding quality and consistency."""
        logger.info("Validating embeddings...")

        validation_results = {
            'valid': True,
            'issues': [],
            'stats': {}
        }

        # Check for null embeddings where text exists
        null_check_query = f"""
        SELECT COUNT(*) as count
        FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        WHERE embedding IS NULL
        AND text_content IS NOT NULL
        AND LENGTH(text_content) > 0
        """

        try:
            result = self.client.execute_query_and_wait(null_check_query)
            null_count = result[0]['count'] if result else 0

            if null_count > 0:
                validation_results['valid'] = False
                validation_results['issues'].append(
                    f"{null_count} documents have text but no embeddings"
                )

        except Exception as e:
            logger.error(f"Failed to validate embeddings: {e}")
            validation_results['valid'] = False
            validation_results['issues'].append(f"Validation error: {e}")

        # Check embedding dimensions
        dimension_query = f"""
        SELECT
            MIN(ARRAY_LENGTH(embedding)) as min_dim,
            MAX(ARRAY_LENGTH(embedding)) as max_dim,
            AVG(ARRAY_LENGTH(embedding)) as avg_dim
        FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        WHERE embedding IS NOT NULL
        """

        try:
            result = self.client.execute_query_and_wait(dimension_query)
            if result:
                dims = result[0]
                validation_results['stats']['embedding_dimensions'] = dims

                if dims['min_dim'] != dims['max_dim']:
                    validation_results['valid'] = False
                    validation_results['issues'].append(
                        f"Inconsistent embedding dimensions: {dims['min_dim']} to {dims['max_dim']}"
                    )

        except Exception as e:
            logger.error(f"Failed to check embedding dimensions: {e}")

        if validation_results['valid']:
            logger.info("Embedding validation passed")
        else:
            logger.warning(f"Embedding validation issues: {validation_results['issues']}")

        return validation_results
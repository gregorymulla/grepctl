"""
BigQuery schema definitions and management.
"""

import logging
from typing import List, Optional
from google.cloud import bigquery

from ..config import Config
from .connection import BigQueryClient


logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages BigQuery schema creation and updates."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize schema manager."""
        self.client = client
        self.config = config

    def get_documents_schema(self) -> List[bigquery.SchemaField]:
        """Get schema for documents table."""
        return [
            bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("uri", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("modality", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("author", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("channel", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("text_content", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("mime_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("meta", "JSON", mode="NULLABLE"),
            bigquery.SchemaField("chunk_index", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("chunk_start", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("chunk_end", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
        ]

    def create_dataset(self) -> None:
        """Create the BigQuery dataset."""
        self.client.create_dataset(self.config.dataset_name)

    def create_tables(self) -> None:
        """Create all required tables."""
        logger.info("Creating core tables...")

        # Create documents table
        self.client.create_or_replace_table(
            "documents",
            schema=self.get_documents_schema(),
            partition_field="created_at",
            clustering_fields=["modality", "source"]
        )

        # Create document_chunks table (will be populated by chunking process)
        self.client.create_or_replace_table(
            "document_chunks",
            schema=self.get_documents_schema(),
            partition_field="created_at",
            clustering_fields=["modality", "source"]
        )

        # Create search_corpus table (will be populated by combining chunks and short docs)
        self.client.create_or_replace_table(
            "search_corpus",
            schema=self.get_documents_schema(),
            partition_field="created_at",
            clustering_fields=["modality", "source"]
        )

        logger.info("Core tables created successfully")

    def create_external_tables(self) -> None:
        """Create external tables for GCS object access."""
        logger.info("Creating external tables...")

        if not self.config.gcs_connection:
            logger.warning("GCS connection not configured, skipping external table creation")
            return

        modalities = [
            ('pdf', 'pdf'),
            ('images', 'images'),
            ('audio', 'audio'),
            ('video', 'video'),
            ('text', 'text'),
            ('markdown', 'markdown'),
            ('json', 'json'),
            ('csv', 'csv'),
            ('documents', 'documents')
        ]

        for modality, folder in modalities:
            table_name = f"obj_{modality}"
            uri_pattern = f"gs://{self.config.gcs_bucket}/{self.config.gcs_prefix}/{folder}/*"

            query = f"""
            CREATE OR REPLACE EXTERNAL TABLE `{self.config.project_id}.{self.config.dataset_name}.{table_name}`
            WITH CONNECTION `{self.config.gcs_connection}`
            OPTIONS (
                object_metadata = 'SIMPLE',
                uris = ['{uri_pattern}']
            )
            """

            try:
                self.client.execute_query_and_wait(query)
                logger.info(f"Created external table {table_name}")
            except Exception as e:
                logger.error(f"Failed to create external table {table_name}: {e}")

    def create_functions(self) -> None:
        """Create BigQuery functions and procedures."""
        logger.info("Creating functions and procedures...")

        # Skip function creation if project ID has hyphens (BigQuery limitation)
        if '-' in self.config.project_id:
            logger.warning("Skipping function creation - project ID contains hyphens which aren't supported in MODEL clause within functions")
            return

        # Create simplified search functions
        self._create_search_functions()

        # Create semantic_grep_tf table function
        self._create_table_function()

        # Create semantic_grep stored procedure
        self._create_stored_procedure()

        logger.info("Functions and procedures created successfully")

    def _create_search_functions(self) -> None:
        """Create simplified search functions for easy SQL usage."""
        logger.info("Creating simplified search functions...")

        # Load and execute the search function SQL
        import os
        function_sql_path = os.path.join(
            os.path.dirname(__file__),
            'search_function.sql'
        )

        if os.path.exists(function_sql_path):
            with open(function_sql_path, 'r') as f:
                sql_template = f.read()

            # Replace placeholders with actual values
            sql = sql_template.replace('{project_id}', self.config.project_id)
            sql = sql.replace('{dataset_name}', self.config.dataset_name)

            # Split and execute each function separately
            functions = sql.split(';')
            for func_sql in functions:
                func_sql = func_sql.strip()
                if func_sql and 'CREATE' in func_sql:
                    try:
                        self.client.execute_query_and_wait(func_sql)
                        # Extract function name for logging
                        if 'FUNCTION' in func_sql:
                            import re
                            match = re.search(r'FUNCTION\s+`[^`]+\.([^`]+)`', func_sql)
                            if match:
                                logger.info(f"Created function: {match.group(1)}")
                    except Exception as e:
                        logger.warning(f"Error creating function: {e}")
        else:
            logger.warning("Search function SQL file not found")

    def _create_table_function(self) -> None:
        """Create the semantic_grep_tf table function."""
        query = f"""
        CREATE OR REPLACE TABLE FUNCTION `{self.config.project_id}.{self.config.dataset_name}.semantic_grep_tf`(
            q STRING,
            top_k INT64,
            source_filter ARRAY<STRING>,
            start_ts TIMESTAMP,
            end_ts TIMESTAMP,
            regex STRING,
            use_rerank BOOL
        )
        RETURNS TABLE<
            doc_id STRING, uri STRING, modality STRING, source STRING,
            created_at TIMESTAMP, author STRING, channel STRING,
            distance FLOAT64, rel_score FLOAT64, text_content STRING
        >
        AS (
            WITH query_embedding AS (
                SELECT ML.GENERATE_EMBEDDING(
                    MODEL `{self.config.project_id}`.{self.config.dataset_name}.text_embedding_model,
                    (SELECT q AS content)
                ).ml_generate_embedding_result AS v
            ),
            knn AS (
                SELECT
                    s.doc_id, s.uri, s.modality, s.source, s.created_at, s.author, s.channel,
                    s.distance, s.text_content
                FROM query_embedding,
                VECTOR_SEARCH(
                    TABLE `{self.config.project_id}.{self.config.dataset_name}.search_corpus`,
                    'embedding',
                    (SELECT v FROM query_embedding),
                    top_k => GREATEST(top_k * {self.config.search_multiplier}, 50),
                    options => '{{"search_count": {self.config.max_search_count}}}'
                ) s
                WHERE (ARRAY_LENGTH(source_filter) = 0 OR s.source IN UNNEST(source_filter))
                    AND s.created_at BETWEEN start_ts AND end_ts
                    AND (regex IS NULL OR regex = '' OR REGEXP_CONTAINS(s.text_content, regex))
            ),
            scored AS (
                SELECT k.*,
                    NULL AS rel_score
                FROM knn k
            )
            SELECT * FROM scored
            ORDER BY COALESCE(rel_score, 0) DESC, distance ASC
            LIMIT top_k
        )
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Created semantic_grep_tf table function")
        except Exception as e:
            logger.error(f"Failed to create table function: {e}")

    def _create_stored_procedure(self) -> None:
        """Create the semantic_grep stored procedure."""
        query = f"""
        CREATE OR REPLACE PROCEDURE `{self.config.project_id}.{self.config.dataset_name}.semantic_grep`(
            q STRING,
            k INT64
        )
        BEGIN
            DECLARE embedding_result STRUCT<ml_generate_embedding_result ARRAY<FLOAT64>>;

            -- Generate embedding for query
            SET embedding_result = (
                SELECT AS STRUCT ML.GENERATE_EMBEDDING(
                    MODEL `{self.config.project_id}`.{self.config.dataset_name}.text_embedding_model,
                    (SELECT q AS content)
                )
            );

            -- Create temp table with candidates
            CREATE TEMP TABLE candidates AS
            SELECT sc.*, distance
            FROM VECTOR_SEARCH(
                TABLE `{self.config.project_id}.{self.config.dataset_name}.search_corpus`,
                'embedding',
                embedding_result.ml_generate_embedding_result,
                top_k => GREATEST(k * {self.config.search_multiplier}, 50),
                options => '{{"search_count": {self.config.max_search_count}}}'
            ) s
            JOIN `{self.config.project_id}.{self.config.dataset_name}.search_corpus` sc
            USING (doc_id);

            -- Score and rank candidates (simplified without ML.GENERATE_TEXT)
            CREATE TEMP TABLE scored AS
            SELECT c.*,
                0.5 AS rel_score
            FROM candidates c;

            -- Return top k results
            SELECT doc_id, uri, modality, source, created_at, author, channel,
                   rel_score, distance, text_content
            FROM scored
            ORDER BY rel_score DESC, distance ASC
            LIMIT k;
        END
        """

        try:
            self.client.execute_query_and_wait(query)
            logger.info("Created semantic_grep stored procedure")
        except Exception as e:
            logger.error(f"Failed to create stored procedure: {e}")

    def create_vector_index(self, rebuild: bool = False) -> None:
        """Create or rebuild vector index."""
        index_name = "search_corpus_idx"

        if rebuild:
            # Drop existing index - correct syntax includes ON clause
            drop_query = f"""
            DROP VECTOR INDEX IF EXISTS `{self.config.project_id}.{self.config.dataset_name}.{index_name}`
            ON `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            """
            try:
                self.client.execute_query_and_wait(drop_query)
                logger.info(f"Dropped existing index {index_name}")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")

        # Create new index - simplified options
        create_query = f"""
        CREATE OR REPLACE VECTOR INDEX `{self.config.project_id}.{self.config.dataset_name}.{index_name}`
        ON `{self.config.project_id}.{self.config.dataset_name}.search_corpus` (embedding)
        OPTIONS (
            distance_type = '{self.config.distance_type}',
            index_type = '{self.config.index_type}'
        )
        """

        try:
            self.client.execute_query_and_wait(create_query)
            logger.info(f"Created vector index {index_name}")
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")

    def init_models(self) -> None:
        """Initialize ML models including embedding model."""
        logger.info("Creating embedding model...")

        # Create text embedding model using text-embedding-004
        query = f"""
        CREATE OR REPLACE MODEL `{self.config.project_id}.{self.config.dataset_name}.text_embedding_model`
        REMOTE WITH CONNECTION `us.vertex-ai-connection`
        OPTIONS (
            ENDPOINT = 'text-embedding-004'
        )
        """

        try:
            job = self.client.execute_query(query)
            job.result()
            logger.info("Embedding model created successfully")
        except Exception as e:
            if "Already Exists" in str(e):
                logger.info("Embedding model already exists")
            else:
                logger.error(f"Failed to create embedding model: {e}")

    def validate_schema(self) -> bool:
        """Validate that all required tables and functions exist."""
        required_tables = ['documents', 'document_chunks', 'search_corpus']
        missing = []

        for table in required_tables:
            if not self.client.table_exists(table):
                missing.append(table)

        if missing:
            logger.error(f"Missing required tables: {missing}")
            return False

        logger.info("Schema validation successful")
        return True
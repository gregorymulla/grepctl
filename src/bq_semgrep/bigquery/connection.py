"""
BigQuery client and connection management.
"""

import logging
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from datetime import datetime

from ..config import Config


logger = logging.getLogger(__name__)


class BigQueryClient:
    """Manages BigQuery connections and operations."""

    def __init__(self, config: Config):
        """Initialize BigQuery client."""
        self.config = config
        self.client = bigquery.Client(
            project=config.project_id,
            location=config.location
        )
        self.dataset_ref = self.client.dataset(config.dataset_name)

    def check_dataset_exists(self, dataset_name: Optional[str] = None) -> bool:
        """Check if dataset exists."""
        dataset_name = dataset_name or self.config.dataset_name
        try:
            self.client.get_dataset(dataset_name)
            return True
        except NotFound:
            return False

    def create_dataset(self, dataset_name: Optional[str] = None) -> bigquery.Dataset:
        """Create dataset if it doesn't exist."""
        dataset_name = dataset_name or self.config.dataset_name
        dataset_id = f"{self.config.project_id}.{dataset_name}"

        if self.check_dataset_exists(dataset_name):
            logger.info(f"Dataset {dataset_name} already exists")
            return self.client.get_dataset(dataset_id)

        dataset = bigquery.Dataset(dataset_id)
        dataset.location = self.config.location
        dataset.description = "Semantic grep dataset for multimodal search"

        dataset = self.client.create_dataset(dataset, exists_ok=True)
        logger.info(f"Created dataset {dataset.dataset_id}")
        return dataset

    def execute_query(self, query: str, job_config: Optional[bigquery.QueryJobConfig] = None) -> bigquery.QueryJob:
        """Execute a BigQuery SQL query."""
        logger.debug(f"Executing query: {query[:200]}...")

        if job_config is None:
            job_config = bigquery.QueryJobConfig()

        job = self.client.query(query, job_config=job_config)
        return job

    def execute_query_and_wait(self, query: str, job_config: Optional[bigquery.QueryJobConfig] = None) -> List[Dict[str, Any]]:
        """Execute query and return results."""
        job = self.execute_query(query, job_config)
        results = job.result()
        return [dict(row) for row in results]

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in dataset."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"
        try:
            self.client.get_table(table_id)
            return True
        except NotFound:
            return False

    def get_table(self, table_name: str) -> Optional[bigquery.Table]:
        """Get table reference."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"
        try:
            return self.client.get_table(table_id)
        except NotFound:
            return None

    def create_or_replace_table(self, table_name: str, schema: List[bigquery.SchemaField],
                                partition_field: Optional[str] = None,
                                clustering_fields: Optional[List[str]] = None) -> bigquery.Table:
        """Create or replace a table with given schema."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"

        table = bigquery.Table(table_id, schema=schema)

        # Add partitioning
        if partition_field:
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field=partition_field
            )

        # Add clustering
        if clustering_fields:
            table.clustering_fields = clustering_fields

        # Delete existing table if it exists
        try:
            self.client.delete_table(table_id)
            logger.info(f"Deleted existing table {table_name}")
        except NotFound:
            pass

        # Create new table
        table = self.client.create_table(table)
        logger.info(f"Created table {table_name}")
        return table

    def insert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> List[Dict]:
        """Insert rows into a table."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"
        table = self.client.get_table(table_id)

        errors = self.client.insert_rows_json(table, rows)
        if errors:
            logger.error(f"Failed to insert rows: {errors}")
        else:
            logger.info(f"Inserted {len(rows)} rows into {table_name}")

        return errors

    def get_document_count(self) -> int:
        """Get total document count."""
        query = f"""
        SELECT COUNT(*) as count
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        """

        try:
            result = self.execute_query_and_wait(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0

    def get_document_stats(self) -> Dict[str, Any]:
        """Get document statistics by modality and source."""
        query = f"""
        SELECT
            modality,
            source,
            COUNT(*) as count,
            MAX(created_at) as latest
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        GROUP BY modality, source
        ORDER BY modality, source
        """

        try:
            results = self.execute_query_and_wait(query)
            return {
                'by_modality': {},
                'by_source': {},
                'total': sum(r['count'] for r in results),
                'latest_update': max((r['latest'] for r in results), default=None)
            }
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return {'by_modality': {}, 'by_source': {}, 'total': 0, 'latest_update': None}

    def get_index_status(self) -> Dict[str, Any]:
        """Get vector index status."""
        query = f"""
        SELECT
            index_name,
            index_status,
            creation_time,
            last_refresh_time
        FROM `{self.config.project_id}.{self.config.dataset_name}.INFORMATION_SCHEMA.VECTOR_INDEXES`
        WHERE index_name = 'search_corpus_idx'
        """

        try:
            results = self.execute_query_and_wait(query)
            if results:
                result = results[0]
                return {
                    'exists': True,
                    'status': result['index_status'],
                    'created': result['creation_time'],
                    'last_updated': result['last_refresh_time']
                }
        except Exception:
            pass

        return {'exists': False}

    def batch_query(self, query: str, batch_size: int = 1000) -> bigquery.QueryJob:
        """Execute a query with batching configuration."""
        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            priority=bigquery.QueryPriority.INTERACTIVE
        )

        return self.execute_query(query, job_config)

    def stream_query_results(self, query: str, page_size: int = 1000):
        """Stream query results in pages."""
        job = self.execute_query(query)

        for page in job.result(page_size=page_size):
            for row in page:
                yield dict(row)

    def load_table_from_json(self, table_name: str, json_rows: List[Dict[str, Any]],
                              write_disposition: str = 'WRITE_APPEND') -> bigquery.LoadJob:
        """Load data into table from JSON rows."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=write_disposition,
            ignore_unknown_values=True,
            autodetect=False
        )

        job = self.client.load_table_from_json(
            json_rows,
            table_id,
            job_config=job_config
        )

        job.result()  # Wait for job to complete
        logger.info(f"Loaded {len(json_rows)} rows into {table_name}")
        return job

    def copy_table(self, source_table: str, destination_table: str,
                   write_disposition: str = 'WRITE_TRUNCATE') -> bigquery.CopyJob:
        """Copy one table to another."""
        source_id = f"{self.config.project_id}.{self.config.dataset_name}.{source_table}"
        dest_id = f"{self.config.project_id}.{self.config.dataset_name}.{destination_table}"

        job_config = bigquery.CopyJobConfig(
            write_disposition=write_disposition
        )

        job = self.client.copy_table(source_id, dest_id, job_config=job_config)
        job.result()  # Wait for job to complete
        logger.info(f"Copied {source_table} to {destination_table}")
        return job

    def delete_table(self, table_name: str) -> None:
        """Delete a table if it exists."""
        table_id = f"{self.config.project_id}.{self.config.dataset_name}.{table_name}"
        try:
            self.client.delete_table(table_id)
            logger.info(f"Deleted table {table_name}")
        except NotFound:
            logger.info(f"Table {table_name} does not exist")

    def get_table_schema(self, table_name: str) -> Optional[List[bigquery.SchemaField]]:
        """Get schema of a table."""
        table = self.get_table(table_name)
        return list(table.schema) if table else None
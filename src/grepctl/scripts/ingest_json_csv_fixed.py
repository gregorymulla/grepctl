#!/usr/bin/env python3
"""
Fixed ingestion for JSON and CSV files using SQL INSERT.
"""

import json
import csv
import io
import logging
import time
from google.cloud import storage
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client(project="semgrep-472018")
bq_client = bigquery.Client(project="semgrep-472018")

def list_files(prefix: str, extension: str):
    """List files in GCS bucket."""
    bucket = storage_client.bucket("gcm-data-lake")
    blobs = bucket.list_blobs(prefix=f"multimodal-dataset/{prefix}/")
    return [f"gs://gcm-data-lake/{blob.name}" for blob in blobs if blob.name.endswith(extension)]

def process_json_file(uri: str):
    """Process a JSON file."""
    try:
        bucket_name = uri.split('/')[2]
        blob_path = '/'.join(uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_text()

        data = json.loads(content)
        filename = uri.split('/')[-1]

        # Build searchable text
        text_parts = [
            f"JSON File: {filename}",
            f"Location: {uri}",
            f"Type: JSON Document",
            ""
        ]

        # Add structure info
        if isinstance(data, dict):
            text_parts.append(f"Root type: Object with {len(data)} keys")
            keys = list(data.keys())[:20]
            text_parts.append(f"Keys: {', '.join(keys)}")

            # Sample content
            text_parts.append("\nSample content:")
            for k, v in list(data.items())[:10]:
                if isinstance(v, (str, int, float, bool)):
                    text_parts.append(f"  {k}: {str(v)[:100]}")
        elif isinstance(data, list):
            text_parts.append(f"Root type: Array with {len(data)} items")
            if data:
                text_parts.append(f"First item type: {type(data[0]).__name__}")

        # Add JSON preview
        json_str = json.dumps(data, indent=2)[:2000]
        if len(json_str) < len(json.dumps(data)):
            json_str += "\n... [truncated]"
        text_parts.append(f"\nData preview:\n{json_str}")

        text_parts.append(f"\nIndexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

        return '\n'.join(text_parts)

    except Exception as e:
        logger.error(f"Error processing {uri}: {e}")
        return None

def process_csv_file(uri: str):
    """Process a CSV file."""
    try:
        bucket_name = uri.split('/')[2]
        blob_path = '/'.join(uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_text()

        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        filename = uri.split('/')[-1]

        # Build searchable text
        text_parts = [
            f"CSV File: {filename}",
            f"Location: {uri}",
            f"Type: CSV Spreadsheet",
            ""
        ]

        if reader.fieldnames:
            text_parts.append(f"Columns ({len(reader.fieldnames)}): {', '.join(reader.fieldnames)}")
            text_parts.append(f"Rows: {len(rows)}")

            # Sample data
            text_parts.append("\nSample data (first 5 rows):")
            for i, row in enumerate(rows[:5], 1):
                values = []
                for k, v in list(row.items())[:5]:
                    val = str(v)[:20] if v else "null"
                    values.append(f"{k}:{val}")
                row_str = ' | '.join(values)
                text_parts.append(f"  Row {i}: {row_str}")

        # Add CSV preview
        csv_lines = content.split('\n')[:30]
        text_parts.append(f"\nData preview:\n" + '\n'.join(csv_lines))

        text_parts.append(f"\nIndexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

        return '\n'.join(text_parts)

    except Exception as e:
        logger.error(f"Error processing {uri}: {e}")
        return None

def insert_document(uri: str, modality: str, text_content: str):
    """Insert a single document using SQL INSERT."""
    query = """
    INSERT INTO `semgrep-472018.grepmm.search_corpus` (uri, modality, text_content)
    VALUES (@uri, @modality, @text_content)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('uri', 'STRING', uri),
            bigquery.ScalarQueryParameter('modality', 'STRING', modality),
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
    """Main ingestion function."""

    logger.info("="*70)
    logger.info("Starting JSON and CSV Ingestion")
    logger.info("="*70)

    # Check existing
    check_query = """
    SELECT modality, COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE modality IN ('json', 'csv')
    GROUP BY modality
    """

    existing_count = {}
    try:
        results = bq_client.query(check_query).result()
        for row in results:
            existing_count[row.modality] = row.count
            logger.info(f"Already have {row.count} {row.modality} files")
    except:
        logger.info("No existing JSON/CSV files found")

    # Get file lists
    json_files = list_files("json", ".json")
    csv_files = list_files("csv", ".csv")

    logger.info(f"Found {len(json_files)} JSON files total")
    logger.info(f"Found {len(csv_files)} CSV files total")

    # Process files (limit to avoid timeout)
    json_processed = 0
    csv_processed = 0

    # Process JSON files
    for uri in json_files[:30]:  # Process first 30
        content = process_json_file(uri)
        if content:
            if insert_document(uri, 'json', content):
                json_processed += 1
                logger.info(f"✓ JSON {json_processed}: {uri.split('/')[-1]}")

    # Process CSV files
    for uri in csv_files[:30]:  # Process first 30
        content = process_csv_file(uri)
        if content:
            if insert_document(uri, 'csv', content):
                csv_processed += 1
                logger.info(f"✓ CSV {csv_processed}: {uri.split('/')[-1]}")

    # Summary
    logger.info("="*70)
    logger.info("JSON/CSV Ingestion Complete!")
    logger.info("="*70)
    logger.info(f"JSON files processed: {json_processed}")
    logger.info(f"CSV files processed: {csv_processed}")
    logger.info(f"Total new documents: {json_processed + csv_processed}")

    if json_processed + csv_processed > 0:
        logger.info("\nNext: Run 'uv run grepctl index --update' to generate embeddings")

if __name__ == "__main__":
    main()
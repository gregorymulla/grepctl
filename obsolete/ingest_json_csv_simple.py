#!/usr/bin/env python3
"""
Simplified ingestion for JSON and CSV files into BigQuery.
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
            text_parts.append(f"Keys: {', '.join(list(data.keys())[:20])}")

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
        text_parts.append(f"\nData preview:\n{json_str}")

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
                row_str = ' | '.join([f"{k}:{v[:20]}" for k, v in list(row.items())[:5]])
                text_parts.append(f"  Row {i}: {row_str}")

        # Add CSV preview
        csv_lines = content.split('\n')[:30]
        text_parts.append(f"\nData preview:\n" + '\n'.join(csv_lines))

        return '\n'.join(text_parts)

    except Exception as e:
        logger.error(f"Error processing {uri}: {e}")
        return None

def main():
    """Main ingestion function."""

    logger.info("Starting JSON and CSV ingestion...")

    # Check existing
    check_query = """
    SELECT modality, COUNT(*) as count
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality IN ('json', 'csv')
    GROUP BY modality
    """

    try:
        results = bq_client.query(check_query).result()
        for row in results:
            logger.info(f"Already have {row.count} {row.modality} files")
    except:
        logger.info("No existing JSON/CSV files found")

    # Get file lists
    json_files = list_files("json", ".json")
    csv_files = list_files("csv", ".csv")

    logger.info(f"Found {len(json_files)} JSON files")
    logger.info(f"Found {len(csv_files)} CSV files")

    # Process files
    documents = []

    # Process first 20 of each type as a test
    for uri in json_files[:20]:
        content = process_json_file(uri)
        if content:
            documents.append({
                'uri': uri,
                'modality': 'json',
                'text_content': content,
                'embedding': None
            })
            logger.info(f"✓ Processed {uri.split('/')[-1]}")

    for uri in csv_files[:20]:
        content = process_csv_file(uri)
        if content:
            documents.append({
                'uri': uri,
                'modality': 'csv',
                'text_content': content,
                'embedding': None
            })
            logger.info(f"✓ Processed {uri.split('/')[-1]}")

    # Insert to BigQuery
    if documents:
        table_id = "semgrep-472018.mmgrep.search_corpus"
        table = bq_client.get_table(table_id)

        errors = bq_client.insert_rows_json(table, documents)

        if errors:
            logger.error(f"Insert errors: {errors}")
        else:
            logger.info(f"✅ Successfully inserted {len(documents)} documents")

    logger.info(f"\nIngestion complete!")
    logger.info(f"  JSON: {len([d for d in documents if d['modality'] == 'json'])}")
    logger.info(f"  CSV: {len([d for d in documents if d['modality'] == 'csv'])}")
    logger.info(f"\nNext: Run 'uv run bq-semgrep index --update' to generate embeddings")

if __name__ == "__main__":
    main()
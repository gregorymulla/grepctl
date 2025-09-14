#!/usr/bin/env python3
"""
Ingest JSON and CSV files into BigQuery for semantic search.
"""

import json
import csv
import io
import logging
import time
from typing import Dict, List, Any, Optional
from google.cloud import storage
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client(project="semgrep-472018")
bq_client = bigquery.Client(project="semgrep-472018")

def process_json_file(uri: str) -> Optional[str]:
    """Process a JSON file and extract searchable content."""

    try:
        # Download JSON from GCS
        bucket_name = uri.split('/')[2]
        blob_name = '/'.join(uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        json_content = blob.download_as_text()

        # Parse JSON
        data = json.loads(json_content)

        # Build searchable content
        filename = uri.split('/')[-1]
        content_parts = [
            f"JSON File: {filename}",
            f"Location: {uri}",
            f"Structure: {get_json_structure(data)}",
            ""
        ]

        # Extract key information
        if isinstance(data, dict):
            content_parts.append(f"Root keys: {', '.join(list(data.keys())[:10])}")

            # Add sample values for searchability
            content_parts.append("\nSample content:")
            for key, value in list(data.items())[:20]:
                if isinstance(value, (str, int, float, bool)):
                    content_parts.append(f"  {key}: {str(value)[:100]}")
                elif isinstance(value, list) and len(value) > 0:
                    content_parts.append(f"  {key}: [{type(value[0]).__name__}...] ({len(value)} items)")
                elif isinstance(value, dict):
                    content_parts.append(f"  {key}: {{...}} ({len(value)} keys)")

        elif isinstance(data, list):
            content_parts.append(f"Array with {len(data)} items")
            if len(data) > 0:
                content_parts.append(f"Item type: {type(data[0]).__name__}")

                # Sample first few items
                content_parts.append("\nSample items:")
                for i, item in enumerate(data[:5]):
                    if isinstance(item, dict):
                        keys = ', '.join(list(item.keys())[:5])
                        content_parts.append(f"  [{i}]: {{{keys}...}}")
                    else:
                        content_parts.append(f"  [{i}]: {str(item)[:100]}")

        # Add full JSON for detailed search (limited to 5000 chars)
        json_str = json.dumps(data, indent=2)[:5000]
        if len(json_str) < len(json.dumps(data)):
            json_str += "\n... [truncated]"
        content_parts.append(f"\nJSON Data:\n{json_str}")

        content_parts.extend([
            "",
            "Analysis: JSON content extracted for semantic search",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"Failed to process JSON {uri}: {e}")
        return None

def process_csv_file(uri: str) -> Optional[str]:
    """Process a CSV file and extract searchable content."""

    try:
        # Download CSV from GCS
        bucket_name = uri.split('/')[2]
        blob_name = '/'.join(uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        csv_content = blob.download_as_text()

        # Parse CSV
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        # Build searchable content
        filename = uri.split('/')[-1]
        content_parts = [
            f"CSV File: {filename}",
            f"Location: {uri}",
            ""
        ]

        # Get headers
        headers = reader.fieldnames
        if headers:
            content_parts.append(f"Columns ({len(headers)}): {', '.join(headers)}")

        # Read sample rows
        rows = list(reader)
        content_parts.append(f"Rows: {len(rows)}")

        if rows:
            # Analyze data types
            content_parts.append("\nColumn Analysis:")
            for header in headers[:10]:  # Analyze first 10 columns
                sample_values = [str(row.get(header, ''))[:50] for row in rows[:5] if row.get(header)]
                if sample_values:
                    content_parts.append(f"  {header}: {', '.join(sample_values[:3])}")

            # Add sample rows for searchability
            content_parts.append("\nSample Data (first 10 rows):")
            for i, row in enumerate(rows[:10]):
                row_str = ' | '.join([f"{k}: {str(v)[:30]}" for k, v in list(row.items())[:5]])
                content_parts.append(f"  Row {i+1}: {row_str}")

            # Add statistics if numeric columns exist
            numeric_cols = []
            for header in headers:
                try:
                    values = [float(row.get(header, 0)) for row in rows[:100] if row.get(header)]
                    if values:
                        numeric_cols.append(header)
                except:
                    pass

            if numeric_cols:
                content_parts.append(f"\nNumeric columns found: {', '.join(numeric_cols[:10])}")

        # Add raw CSV preview (limited)
        csv_preview = csv_content[:3000]
        if len(csv_preview) < len(csv_content):
            csv_preview += "\n... [truncated]"
        content_parts.append(f"\nCSV Preview:\n{csv_preview}")

        content_parts.extend([
            "",
            "Analysis: CSV content extracted for semantic search",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"Failed to process CSV {uri}: {e}")
        return None

def get_json_structure(obj: Any, max_depth: int = 3, current_depth: int = 0) -> str:
    """Get a string representation of JSON structure."""

    if current_depth >= max_depth:
        return "..."

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        keys = list(obj.keys())[:5]
        if len(obj) > 5:
            keys.append("...")
        return "{" + ", ".join(keys) + "}"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        return f"[{type(obj[0]).__name__}...] ({len(obj)} items)"
    else:
        return type(obj).__name__

def insert_to_bigquery(documents: List[Dict[str, Any]]) -> int:
    """Insert documents into BigQuery."""

    if not documents:
        return 0

    # Prepare rows for insertion
    rows_to_insert = []
    for doc in documents:
        rows_to_insert.append({
            'uri': doc['uri'],
            'modality': doc['modality'],
            'text_content': doc['text_content'],
            'embedding': None  # Will be generated later
        })

    # Insert into BigQuery
    table_id = "semgrep-472018.mmgrep.search_corpus"
    table = bq_client.get_table(table_id)

    errors = bq_client.insert_rows_json(table, rows_to_insert)

    if errors:
        logger.error(f"Failed to insert rows: {errors}")
        return 0

    return len(rows_to_insert)

def main():
    """Main function to ingest JSON and CSV files."""

    logger.info("="*70)
    logger.info("Starting JSON and CSV Ingestion")
    logger.info("="*70)

    # Get list of JSON files
    json_query = """
    SELECT DISTINCT uri
    FROM `semgrep-472018.mmgrep.obj_json`
    ORDER BY uri
    """

    # Get list of CSV files
    csv_query = """
    SELECT DISTINCT uri
    FROM `semgrep-472018.mmgrep.obj_csv`
    ORDER BY uri
    """

    # Check if files are already ingested
    existing_query = """
    SELECT uri
    FROM `semgrep-472018.mmgrep.search_corpus`
    WHERE modality IN ('json', 'csv')
    """

    existing_results = bq_client.query(existing_query).result()
    existing_uris = {row.uri for row in existing_results}

    if existing_uris:
        logger.info(f"Found {len(existing_uris)} JSON/CSV files already ingested")

    # Process JSON files
    json_results = bq_client.query(json_query).result()
    json_uris = [row.uri for row in json_results if row.uri not in existing_uris]

    logger.info(f"Found {len(json_uris)} new JSON files to process")

    json_documents = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_json_file, uri): uri for uri in json_uris[:50]}  # Process first 50

        for future in as_completed(futures):
            uri = futures[future]
            try:
                content = future.result()
                if content:
                    json_documents.append({
                        'uri': uri,
                        'modality': 'json',
                        'text_content': content
                    })
                    logger.info(f"✓ Processed JSON: {uri.split('/')[-1]}")
                else:
                    logger.error(f"✗ Failed JSON: {uri.split('/')[-1]}")
            except Exception as e:
                logger.error(f"✗ Error processing {uri}: {e}")

    # Process CSV files
    csv_results = bq_client.query(csv_query).result()
    csv_uris = [row.uri for row in csv_results if row.uri not in existing_uris]

    logger.info(f"Found {len(csv_uris)} new CSV files to process")

    csv_documents = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_csv_file, uri): uri for uri in csv_uris[:50]}  # Process first 50

        for future in as_completed(futures):
            uri = futures[future]
            try:
                content = future.result()
                if content:
                    csv_documents.append({
                        'uri': uri,
                        'modality': 'csv',
                        'text_content': content
                    })
                    logger.info(f"✓ Processed CSV: {uri.split('/')[-1]}")
                else:
                    logger.error(f"✗ Failed CSV: {uri.split('/')[-1]}")
            except Exception as e:
                logger.error(f"✗ Error processing {uri}: {e}")

    # Insert all documents to BigQuery
    all_documents = json_documents + csv_documents

    if all_documents:
        logger.info(f"\nInserting {len(all_documents)} documents to BigQuery...")
        inserted = insert_to_bigquery(all_documents)
        logger.info(f"Successfully inserted {inserted} documents")

    # Summary
    logger.info("="*70)
    logger.info("JSON/CSV Ingestion Complete!")
    logger.info("="*70)
    logger.info(f"JSON files processed: {len(json_documents)}")
    logger.info(f"CSV files processed: {len(csv_documents)}")
    logger.info(f"Total new documents: {len(all_documents)}")

    if all_documents:
        logger.info("\nNext: Run 'uv run bq-semgrep index --update' to generate embeddings")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Update images with descriptions from the image_descriptions table.
This script syncs image descriptions to enable accurate semantic search.
"""

import time
from google.cloud import bigquery
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize BigQuery client
bq_client = bigquery.Client(project="semgrep-472018")

def get_image_descriptions() -> Dict[str, Dict]:
    """Fetch all image descriptions from the image_descriptions table."""
    query = """
    SELECT
        uri,
        description,
        tags
    FROM `semgrep-472018.grepmm.image_descriptions`
    """

    results = bq_client.query(query).result()
    descriptions = {}
    for row in results:
        descriptions[row.uri] = {
            'description': row.description,
            'tags': row.tags if row.tags else []
        }

    logger.info(f"Loaded {len(descriptions)} image descriptions")
    return descriptions

def get_image_metadata(image_uri: str) -> Dict:
    """Get image metadata from obj_images table."""
    query = """
    SELECT
        size,
        content_type,
        updated
    FROM `semgrep-472018.grepmm.obj_images`
    WHERE uri = @uri
    LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("uri", "STRING", image_uri),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()
    for row in results:
        return {
            'size': row.size,
            'content_type': row.content_type,
            'updated': row.updated
        }
    return None

def update_image_with_description(image_uri: str, description_data: Dict) -> bool:
    """Update a single image in search_corpus with its description."""
    try:
        filename = image_uri.split('/')[-1]

        # Get image metadata
        metadata = get_image_metadata(image_uri)
        if not metadata:
            logger.warning(f"No metadata found for {filename}")
            return False

        # Build rich text content
        description_parts = []
        description_parts.append(f"Image: {filename}")
        description_parts.append("")
        description_parts.append(f"Description: {description_data['description']}")
        description_parts.append("")

        if description_data['tags']:
            description_parts.append(f"Tags: {', '.join(description_data['tags'])}")

        # Add file format and size
        format_type = filename.split('.')[-1].upper() if '.' in filename else 'UNKNOWN'
        description_parts.append(f"Format: {format_type}")
        description_parts.append(f"Size: {metadata['size']:,} bytes")

        # Add mime type if different from format
        if metadata['content_type']:
            description_parts.append(f"Type: {metadata['content_type']}")

        description_parts.append("")
        description_parts.append(f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

        text_content = '\n'.join(description_parts)

        # Update in search_corpus
        update_query = """
        UPDATE `semgrep-472018.grepmm.search_corpus`
        SET text_content = @text_content
        WHERE uri = @uri AND modality = 'image'
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("uri", "STRING", image_uri),
                bigquery.ScalarQueryParameter("text_content", "STRING", text_content),
            ]
        )

        job = bq_client.query(update_query, job_config=job_config)
        result = job.result()

        if job.num_dml_affected_rows > 0:
            logger.info(f"✓ {filename} - Description: '{description_data['description'][:50]}...'")
            return True
        else:
            logger.warning(f"⚠ {filename} - No rows updated (might not exist in search_corpus)")
            return False

    except Exception as e:
        logger.error(f"✗ {image_uri.split('/')[-1]}: {e}")
        return False

def ensure_descriptions_exist():
    """Ensure image_descriptions table exists and has data."""
    # Check if table exists
    check_table_query = """
    SELECT COUNT(*) as count
    FROM `semgrep-472018.grepmm.image_descriptions`
    """

    try:
        result = bq_client.query(check_table_query).result()
        for row in result:
            if row.count == 0:
                logger.error("image_descriptions table is empty!")
                logger.info("Please run: uv run grepctl images --setup --add-descriptions")
                return False
            logger.info(f"Found {row.count} image descriptions in table")
            return True
    except Exception as e:
        logger.error(f"image_descriptions table not found: {e}")
        logger.info("Please run: uv run grepctl images --setup --add-descriptions")
        return False

def main():
    logger.info("Updating images with descriptions for semantic search...")
    logger.info("="*60)

    # Check prerequisites
    if not ensure_descriptions_exist():
        return

    # Use batch update for better performance
    logger.info("Performing batch update of all images with descriptions...")

    batch_query = """
    UPDATE `semgrep-472018.grepmm.search_corpus` sc
    SET text_content = CONCAT(
        'Image: ', REGEXP_EXTRACT(sc.uri, r'/([^/]+)$'), '\\n\\n',
        'Description: ', d.description, '\\n\\n',
        'Tags: ', ARRAY_TO_STRING(d.tags, ', '), '\\n',
        'Format: ', UPPER(REGEXP_EXTRACT(sc.uri, r'\\.([^.]+)$')), '\\n',
        'Size: ', CAST(i.size AS STRING), ' bytes\\n',
        'Type: ', i.content_type, '\\n\\n',
        'Indexed: ', CAST(CURRENT_TIMESTAMP() AS STRING)
    )
    FROM `semgrep-472018.grepmm.image_descriptions` d
    JOIN `semgrep-472018.grepmm.obj_images` i ON d.uri = i.uri
    WHERE sc.uri = d.uri AND sc.modality = 'image'
    """

    try:
        job = bq_client.query(batch_query)
        result = job.result()

        rows_updated = job.num_dml_affected_rows
        logger.info(f"✓ Batch update completed: {rows_updated} images updated")

        # Verify the update
        check_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN text_content LIKE '%Description:%' THEN 1 ELSE 0 END) as with_descriptions
        FROM `semgrep-472018.grepmm.search_corpus`
        WHERE modality = 'image'
        """

        check_result = bq_client.query(check_query).result()
        for row in check_result:
            logger.info(f"\n{'='*60}")
            logger.info(f"Image Description Update Complete!")
            logger.info(f"Total images: {row.total}")
            logger.info(f"Images with descriptions: {row.with_descriptions}")

            if row.with_descriptions > 0:
                logger.info(f"Success rate: {row.with_descriptions}/{row.total} ({100*row.with_descriptions/row.total:.1f}%)")
                logger.info(f"\nNext steps:")
                logger.info(f"1. Regenerate embeddings: uv run grepctl index --update")
                logger.info(f"2. Test search: uv run grepctl search 'bird' --top-k 5")
            else:
                logger.error("\nNo images have descriptions. Please check the setup.")

    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        logger.info("Please ensure image_descriptions table is properly populated.")
        logger.info("Run: uv run grepctl images --setup --add-descriptions")

if __name__ == "__main__":
    main()
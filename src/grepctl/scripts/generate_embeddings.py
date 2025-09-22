#!/usr/bin/env python3
"""
Generate embeddings for documents in the search corpus.
"""

import logging
import time
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_embeddings_batch(batch_size: int = 100):
    """Generate embeddings in batches."""

    client = bigquery.Client(project='semgrep-472018')

    # First, check how many documents need embeddings
    check_query = """
    SELECT COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
    AND text_content IS NOT NULL
    AND LENGTH(text_content) > 0
    """

    result = client.query(check_query).result()
    docs_needing_embeddings = list(result)[0].count

    logger.info(f"Documents needing embeddings: {docs_needing_embeddings}")

    if docs_needing_embeddings == 0:
        logger.info("All documents already have embeddings!")
        return

    # Process in batches
    total_processed = 0
    batch_num = 0

    while total_processed < docs_needing_embeddings:
        batch_num += 1
        logger.info(f"\nProcessing batch {batch_num} (size: {batch_size})...")

        # Generate embeddings for a batch
        update_query = f"""
        UPDATE `semgrep-472018.grepmm.search_corpus` AS sc
        SET embedding = emb.ml_generate_embedding_result
        FROM (
            SELECT
                doc_id,
                ml_generate_embedding_result
            FROM ML.GENERATE_EMBEDDING(
                MODEL `semgrep-472018.grepmm.text_embedding_model`,
                (
                    SELECT
                        doc_id,
                        text_content AS content
                    FROM `semgrep-472018.grepmm.search_corpus`
                    WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
                    AND text_content IS NOT NULL
                    AND LENGTH(text_content) > 0
                    LIMIT {batch_size}
                ),
                STRUCT(TRUE AS flatten_json_output)
            )
        ) AS emb
        WHERE sc.doc_id = emb.doc_id
        """

        try:
            job = client.query(update_query)
            job.result()  # Wait for job to complete

            # Check how many were updated
            rows_updated = job.num_dml_affected_rows
            total_processed += rows_updated

            logger.info(f"✓ Updated {rows_updated} documents with embeddings")
            logger.info(f"  Total progress: {total_processed}/{docs_needing_embeddings}")

            if rows_updated == 0:
                logger.warning("No rows updated in this batch, stopping")
                break

            # Small delay between batches
            if total_processed < docs_needing_embeddings:
                time.sleep(2)

        except Exception as e:
            logger.error(f"Error in batch {batch_num}: {e}")
            break

    # Final status check
    final_check = """
    SELECT
        COUNT(*) as total_docs,
        SUM(CASE WHEN embedding IS NOT NULL AND ARRAY_LENGTH(embedding) > 0 THEN 1 ELSE 0 END) as docs_with_embeddings
    FROM `semgrep-472018.grepmm.search_corpus`
    """

    result = client.query(final_check).result()
    row = list(result)[0]

    logger.info("="*70)
    logger.info("Embedding Generation Complete!")
    logger.info(f"Total documents: {row.total_docs}")
    logger.info(f"Documents with embeddings: {row.docs_with_embeddings}")
    logger.info(f"Completion rate: {row.docs_with_embeddings/row.total_docs*100:.1f}%")
    logger.info("="*70)

if __name__ == "__main__":
    # Process in batches of 500
    generate_embeddings_batch(batch_size=500)
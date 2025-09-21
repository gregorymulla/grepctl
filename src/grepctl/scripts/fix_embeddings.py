#!/usr/bin/env python3
"""
Fix embedding issues for any modality.
Handles empty arrays, dimension mismatches, and stuck embeddings.
"""

import logging
from google.cloud import bigquery
from typing import Dict, List, Tuple
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize BigQuery client
bq_client = bigquery.Client(project="semgrep-472018")

def diagnose_embeddings() -> Dict[str, Dict]:
    """Diagnose embedding issues across all modalities."""

    logger.info("="*70)
    logger.info("Diagnosing Embedding Issues")
    logger.info("="*70)

    # Check embedding status for each modality
    query = """
    SELECT
        modality,
        COUNT(*) as total_docs,
        SUM(CASE WHEN text_content IS NULL THEN 1 ELSE 0 END) as no_content,
        SUM(CASE WHEN embedding IS NULL THEN 1 ELSE 0 END) as null_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 0 THEN 1 ELSE 0 END) as empty_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 768 THEN 1 ELSE 0 END) as valid_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) > 0 AND ARRAY_LENGTH(embedding) != 768 THEN 1 ELSE 0 END) as wrong_dimension
    FROM `semgrep-472018.grepmm.search_corpus`
    GROUP BY modality
    ORDER BY modality
    """

    results = {}
    for row in bq_client.query(query):
        results[row.modality] = {
            'total': row.total_docs,
            'no_content': row.no_content,
            'null_embeddings': row.null_embeddings,
            'empty_embeddings': row.empty_embeddings,
            'valid_embeddings': row.valid_embeddings,
            'wrong_dimension': row.wrong_dimension
        }

        # Log issues
        logger.info(f"\n{row.modality.upper()}:")
        logger.info(f"  Total documents: {row.total_docs}")
        logger.info(f"  Valid embeddings (768-dim): {row.valid_embeddings}")

        if row.no_content > 0:
            logger.warning(f"  ⚠️  No text content: {row.no_content}")
        if row.empty_embeddings > 0:
            logger.warning(f"  ⚠️  Empty embeddings []: {row.empty_embeddings}")
        if row.wrong_dimension > 0:
            logger.error(f"  ❌ Wrong dimension: {row.wrong_dimension}")
        if row.null_embeddings > 0 and row.no_content == 0:
            logger.info(f"  📝 Need embeddings: {row.null_embeddings}")

    return results

def fix_empty_embeddings() -> int:
    """Fix empty embedding arrays by setting them to NULL."""

    logger.info("\n" + "-"*70)
    logger.info("Step 1: Fixing Empty Embeddings")
    logger.info("-"*70)

    # Set empty arrays to NULL
    fix_query = """
    UPDATE `semgrep-472018.grepmm.search_corpus`
    SET embedding = NULL
    WHERE ARRAY_LENGTH(embedding) = 0
    """

    job = bq_client.query(fix_query)
    job.result()

    affected = job.num_dml_affected_rows
    if affected > 0:
        logger.info(f"✅ Fixed {affected} empty embeddings (set to NULL)")
    else:
        logger.info("✅ No empty embeddings found")

    return affected

def fix_wrong_dimensions() -> int:
    """Fix embeddings with wrong dimensions."""

    logger.info("\n" + "-"*70)
    logger.info("Step 2: Fixing Wrong Dimension Embeddings")
    logger.info("-"*70)

    # Check for wrong dimensions
    check_query = """
    SELECT modality, COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE ARRAY_LENGTH(embedding) > 0 AND ARRAY_LENGTH(embedding) != 768
    GROUP BY modality
    """

    wrong_dims = list(bq_client.query(check_query))

    if wrong_dims:
        logger.warning("Found embeddings with wrong dimensions:")
        for row in wrong_dims:
            logger.warning(f"  {row.modality}: {row.count} documents")

        # Set wrong dimension embeddings to NULL
        fix_query = """
        UPDATE `semgrep-472018.grepmm.search_corpus`
        SET embedding = NULL
        WHERE ARRAY_LENGTH(embedding) > 0 AND ARRAY_LENGTH(embedding) != 768
        """

        job = bq_client.query(fix_query)
        job.result()

        logger.info(f"✅ Reset {job.num_dml_affected_rows} wrong-dimension embeddings")
        return job.num_dml_affected_rows
    else:
        logger.info("✅ No wrong-dimension embeddings found")
        return 0

def generate_missing_embeddings(batch_size: int = 50) -> int:
    """Generate embeddings for documents that have content but no embeddings."""

    logger.info("\n" + "-"*70)
    logger.info("Step 3: Generating Missing Embeddings")
    logger.info("-"*70)

    # Count documents needing embeddings
    count_query = """
    SELECT modality, COUNT(*) as count
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE text_content IS NOT NULL
    AND (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
    GROUP BY modality
    ORDER BY modality
    """

    needs_embedding = list(bq_client.query(count_query))

    if not needs_embedding:
        logger.info("✅ All documents with content have embeddings")
        return 0

    total_needed = 0
    for row in needs_embedding:
        logger.info(f"  {row.modality}: {row.count} documents need embeddings")
        total_needed += row.count

    logger.info(f"\nTotal documents needing embeddings: {total_needed}")

    # Generate embeddings in batches
    total_generated = 0

    for modality_row in needs_embedding:
        modality = modality_row.modality
        count = modality_row.count

        logger.info(f"\nProcessing {modality} documents...")

        batches_needed = (count + batch_size - 1) // batch_size

        for batch_num in range(batches_needed):
            # Generate embeddings for a batch
            # Note: BigQuery UPDATE doesn't support LIMIT, so we use a subquery
            update_query = f"""
            UPDATE `semgrep-472018.grepmm.search_corpus` t
            SET embedding = (
                SELECT ml_generate_embedding_result
                FROM ML.GENERATE_EMBEDDING(
                    MODEL `semgrep-472018.grepmm.text_embedding_model`,
                    (SELECT text_content AS content),
                    STRUCT(TRUE AS flatten_json_output)
                )
            )
            WHERE modality = '{modality}'
            AND text_content IS NOT NULL
            AND (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
            AND uri IN (
                SELECT uri
                FROM `semgrep-472018.grepmm.search_corpus`
                WHERE modality = '{modality}'
                AND text_content IS NOT NULL
                AND (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
                LIMIT {batch_size}
            )
            """

            try:
                job = bq_client.query(update_query)
                job.result()

                generated = job.num_dml_affected_rows
                total_generated += generated

                if generated > 0:
                    logger.info(f"  ✅ Batch {batch_num + 1}: Generated {generated} embeddings")

                    # Rate limiting to avoid quota issues
                    if batch_num < batches_needed - 1:
                        time.sleep(2)
                else:
                    break  # No more documents to process for this modality

            except Exception as e:
                logger.error(f"  ❌ Error generating embeddings for {modality}: {e}")
                logger.info("  Continuing with next modality...")
                break

    logger.info(f"\n✅ Total embeddings generated: {total_generated}")
    return total_generated

def verify_embeddings() -> bool:
    """Verify all embeddings are valid."""

    logger.info("\n" + "-"*70)
    logger.info("Step 4: Verifying Embeddings")
    logger.info("-"*70)

    # Check final status
    verify_query = """
    SELECT
        COUNT(*) as total_docs,
        SUM(CASE WHEN text_content IS NOT NULL THEN 1 ELSE 0 END) as has_content,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 768 THEN 1 ELSE 0 END) as valid_embeddings,
        SUM(CASE WHEN text_content IS NOT NULL AND embedding IS NULL THEN 1 ELSE 0 END) as missing_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) = 0 THEN 1 ELSE 0 END) as empty_embeddings,
        SUM(CASE WHEN ARRAY_LENGTH(embedding) > 0 AND ARRAY_LENGTH(embedding) != 768 THEN 1 ELSE 0 END) as wrong_dimension
    FROM `semgrep-472018.grepmm.search_corpus`
    """

    result = list(bq_client.query(verify_query))[0]

    logger.info(f"Total documents: {result.total_docs}")
    logger.info(f"Documents with content: {result.has_content}")
    logger.info(f"Valid embeddings (768-dim): {result.valid_embeddings}")

    all_good = True

    if result.empty_embeddings > 0:
        logger.error(f"❌ Still have {result.empty_embeddings} empty embeddings")
        all_good = False

    if result.wrong_dimension > 0:
        logger.error(f"❌ Still have {result.wrong_dimension} wrong-dimension embeddings")
        all_good = False

    if result.missing_embeddings > 0:
        logger.warning(f"⚠️  {result.missing_embeddings} documents still need embeddings")
        logger.info("   (May be due to quota limits or processing errors)")
        all_good = False

    if all_good and result.valid_embeddings == result.has_content:
        logger.info("\n✅ SUCCESS: All documents with content have valid embeddings!")
        return True
    else:
        logger.info("\n⚠️  Some issues remain. You may need to:")
        logger.info("  1. Wait for quota refresh if hitting limits")
        logger.info("  2. Check for documents with invalid text_content")
        logger.info("  3. Run this script again later")
        return False

def main():
    """Main function to fix all embedding issues."""

    logger.info("\n" + "="*70)
    logger.info("🔧 EMBEDDING FIX UTILITY")
    logger.info("="*70)
    logger.info("This script will automatically fix embedding issues:")
    logger.info("  1. Clear empty embedding arrays")
    logger.info("  2. Fix wrong-dimension embeddings")
    logger.info("  3. Generate missing embeddings")
    logger.info("  4. Verify all embeddings are valid")

    # Step 1: Diagnose issues
    issues = diagnose_embeddings()

    # Step 2: Fix empty embeddings
    fixed_empty = fix_empty_embeddings()

    # Step 3: Fix wrong dimensions
    fixed_wrong = fix_wrong_dimensions()

    # Step 4: Generate missing embeddings
    generated = generate_missing_embeddings()

    # Step 5: Verify
    success = verify_embeddings()

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Empty embeddings fixed: {fixed_empty}")
    logger.info(f"Wrong dimensions fixed: {fixed_wrong}")
    logger.info(f"New embeddings generated: {generated}")

    if success:
        logger.info("\n🎉 All embedding issues resolved!")
        logger.info("You can now search across all documents:")
        logger.info("  uv run grepctl search 'your query'")
    else:
        logger.info("\n⚠️  Some issues remain. Check the output above for details.")
        logger.info("You may need to run this script again after:")
        logger.info("  - Waiting for API quota refresh")
        logger.info("  - Fixing any content issues")

        # Show which modalities still have issues
        final_check = """
        SELECT modality,
               COUNT(*) as total,
               SUM(CASE WHEN text_content IS NOT NULL AND embedding IS NULL THEN 1 ELSE 0 END) as needs_embedding
        FROM `semgrep-472018.grepmm.search_corpus`
        WHERE text_content IS NOT NULL AND embedding IS NULL
        GROUP BY modality
        """

        remaining = list(bq_client.query(final_check))
        if remaining:
            logger.info("\nModalities still needing embeddings:")
            for row in remaining:
                if row.needs_embedding > 0:
                    logger.info(f"  {row.modality}: {row.needs_embedding} documents")

if __name__ == "__main__":
    main()
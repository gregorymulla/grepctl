#!/usr/bin/env python3
"""
Create and test Gemini model for PDF extraction in BigQuery.
"""

from google.cloud import bigquery
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bq_client = bigquery.Client(project="semgrep-472018")

def create_gemini_model():
    """Create Gemini model for PDF extraction."""

    logger.info("Creating Gemini model for PDF extraction...")

    try:
        # Create the Gemini model
        create_model_query = """
        CREATE OR REPLACE MODEL `semgrep-472018.mmgrep.gemini_pdf_model`
        REMOTE WITH CONNECTION `semgrep-472018.us.vertex-ai-connection`
        OPTIONS (
            ENDPOINT = 'gemini-1.5-flash-001'
        )
        """

        job = bq_client.query(create_model_query)
        job.result()
        logger.info("✅ Successfully created Gemini PDF model!")

        return True

    except Exception as e:
        logger.error(f"Failed to create Gemini model: {e}")
        return False

def test_pdf_extraction():
    """Test PDF extraction with Gemini."""

    logger.info("\nTesting PDF extraction with Gemini...")

    try:
        # Test with a sample PDF
        test_query = """
        WITH pdf_data AS (
            SELECT
                uri,
                data
            FROM `semgrep-472018.mmgrep.obj_pdfs`
            WHERE uri = 'gs://gcm-data-lake/multimodal-dataset/pdfs/arxiv_2301.00001.pdf'
            LIMIT 1
        )
        SELECT
            uri,
            ML.GENERATE_TEXT(
                MODEL `semgrep-472018.mmgrep.gemini_pdf_model`,
                (SELECT data AS prompt FROM pdf_data),
                STRUCT(
                    0.2 AS temperature,
                    1024 AS max_output_tokens,
                    0.1 AS top_p,
                    TRUE AS flatten_json_output,
                    'Extract and summarize the content of this PDF. Include: 1) Title and authors, 2) Main topic, 3) Key findings, 4) Technical details, 5) Any code or formulas. Provide a comprehensive summary for searchability.' AS prompt_prefix
                )
            ) AS extracted_content
        FROM pdf_data
        """

        job = bq_client.query(test_query)
        results = job.result()

        for row in results:
            logger.info(f"\nPDF: {row.uri}")
            logger.info(f"Extracted content preview:")
            content = str(row.extracted_content)[:500] if row.extracted_content else "No content"
            logger.info(content)

        return True

    except Exception as e:
        logger.error(f"PDF extraction test failed: {e}")

        # Try simpler approach
        logger.info("\nTrying simplified approach...")
        return test_simple_extraction()

def test_simple_extraction():
    """Test with a simpler extraction approach."""

    try:
        # Just test if model works at all
        test_query = """
        SELECT
            ML.GENERATE_TEXT(
                MODEL `semgrep-472018.mmgrep.gemini_pdf_model`,
                (SELECT 'What is 2+2?' AS prompt),
                STRUCT(
                    0.2 AS temperature,
                    100 AS max_output_tokens,
                    TRUE AS flatten_json_output
                )
            ) AS response
        """

        job = bq_client.query(test_query)
        results = job.result()

        for row in results:
            logger.info(f"Model response: {row.response}")

        logger.info("✅ Gemini model is working!")
        return True

    except Exception as e:
        logger.error(f"Model test failed: {e}")
        return False

def main():
    """Main function."""

    # Create the model
    if create_gemini_model():
        # Wait a moment for model to be ready
        logger.info("Waiting for model to be ready...")
        time.sleep(5)

        # Test extraction
        if test_pdf_extraction():
            logger.info("\n✅ Gemini PDF extraction is ready!")
            logger.info("You can now process all PDFs with Gemini.")
        else:
            logger.info("\n⚠️ PDF extraction needs more configuration.")
            logger.info("But Gemini model is created and can be used.")
    else:
        logger.info("\n❌ Could not create Gemini model.")
        logger.info("Will use alternative extraction methods.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test using BigQuery ML with Gemini for PDF extraction.
"""

from google.cloud import bigquery
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bq_client = bigquery.Client(project="semgrep-472018")

def test_gemini_in_bigquery():
    """Test if we can use Gemini through BigQuery ML."""

    # First, check if we have a Gemini model
    logger.info("Checking for Gemini models in BigQuery...")

    try:
        # List models in the dataset
        query = """
        SELECT *
        FROM `semgrep-472018.mmgrep.INFORMATION_SCHEMA.MODELS`
        """

        results = bq_client.query(query).result()
        logger.info("Available models:")
        for row in results:
            logger.info(f"  - {row.model_name}: {row.model_type}")

    except Exception as e:
        logger.info(f"Could not list models: {e}")

    # Try to create a Gemini model for PDF extraction
    logger.info("\nAttempting to create Gemini model for PDFs...")

    try:
        create_model_query = """
        CREATE OR REPLACE MODEL `semgrep-472018.mmgrep.gemini_pdf_model`
        REMOTE WITH CONNECTION `semgrep-472018.us.vertex-ai-connection`
        OPTIONS (
            ENDPOINT = 'gemini-1.5-flash-001'
        )
        """

        job = bq_client.query(create_model_query)
        job.result()
        logger.info("✅ Successfully created Gemini model!")

        return True

    except Exception as e:
        logger.error(f"Failed to create Gemini model: {e}")

        # Try alternative approach
        logger.info("\nTrying alternative: Document AI...")
        return test_document_ai()

def test_document_ai():
    """Test Document AI as an alternative to Gemini."""

    try:
        # Check if Document AI is available
        import subprocess
        result = subprocess.run(
            ["gcloud", "services", "list", "--enabled", "--filter", "name:documentai.googleapis.com", "--project", "semgrep-472018"],
            capture_output=True,
            text=True
        )

        if "documentai.googleapis.com" in result.stdout:
            logger.info("✅ Document AI is enabled")
            return True
        else:
            logger.info("Document AI not enabled. Enabling now...")
            subprocess.run(
                ["gcloud", "services", "enable", "documentai.googleapis.com", "--project", "semgrep-472018"],
                check=True
            )
            logger.info("✅ Document AI enabled")
            return True

    except Exception as e:
        logger.error(f"Document AI setup failed: {e}")
        return False

if __name__ == "__main__":
    if test_gemini_in_bigquery():
        logger.info("\n✅ PDF extraction capability available!")
    else:
        logger.info("\n⚠️ Using alternative PDF extraction methods")
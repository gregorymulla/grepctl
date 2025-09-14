#!/usr/bin/env python3
"""
Test Gemini API for PDF content extraction.
"""

import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
vertexai.init(project="semgrep-472018", location="us-central1")

def test_gemini_pdf():
    """Test Gemini's ability to extract content from PDFs."""

    # Test with a sample PDF
    pdf_uri = "gs://gcm-data-lake/multimodal-dataset/pdfs/arxiv_2301.00001.pdf"

    logger.info(f"Testing Gemini with PDF: {pdf_uri}")

    try:
        # Initialize Gemini model
        model = GenerativeModel("gemini-1.5-flash")

        # Create a Part from the PDF
        pdf_part = Part.from_uri(
            uri=pdf_uri,
            mime_type="application/pdf"
        )

        # Generate content extraction
        prompt = """
        Please extract and summarize the content of this PDF document.
        Include:
        1. Title and authors
        2. Main topic/subject
        3. Key findings or conclusions
        4. Important technical details
        5. Any code, formulas, or algorithms mentioned

        Provide a comprehensive summary that would help someone search for this document.
        """

        response = model.generate_content([pdf_part, prompt])

        logger.info("Successfully extracted content from PDF!")
        logger.info("-" * 60)
        print(response.text)
        logger.info("-" * 60)

        return True

    except Exception as e:
        logger.error(f"Failed to process PDF with Gemini: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_gemini_pdf()
    if success:
        logger.info("\n✅ Gemini PDF extraction is working!")
        logger.info("Ready to process all PDFs with Gemini.")
    else:
        logger.info("\n❌ Gemini PDF extraction failed.")
        logger.info("May need to enable additional APIs or check permissions.")
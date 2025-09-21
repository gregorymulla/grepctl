#!/usr/bin/env python3
"""
Hybrid PDF extraction using Document AI with PyPDF2 fallback.
"""

from google.cloud import documentai_v1 as documentai
from google.cloud import storage
from google.cloud import bigquery
import PyPDF2
import io
import logging
import time
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client(project="semgrep-472018")
bq_client = bigquery.Client(project="semgrep-472018")
docai_client = documentai.DocumentProcessorServiceClient()

# Document AI processor (already created)
PROCESSOR_NAME = "projects/936777684453/locations/us/processors/967b0c6daf70d715"

def extract_with_pypdf2(pdf_uri: str) -> Optional[str]:
    """Extract text from PDF using PyPDF2."""

    try:
        # Download PDF from GCS
        bucket_name = pdf_uri.split('/')[2]
        blob_name = '/'.join(pdf_uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        pdf_bytes = blob.download_as_bytes()

        # Extract text with PyPDF2
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        extracted_text = []
        num_pages = len(pdf_reader.pages)

        for page_num in range(min(num_pages, 20)):  # Limit to first 20 pages
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text:
                extracted_text.append(text)

        # Build content
        filename = pdf_uri.split('/')[-1]
        content_parts = [
            f"PDF File: {filename}",
            f"Location: {pdf_uri}",
            f"Pages: {num_pages}",
            f"Extraction Method: PyPDF2",
            "",
            "Content:",
        ]

        full_text = '\n'.join(extracted_text)
        if full_text:
            # Clean up text
            full_text = full_text.replace('\n\n\n', '\n\n').strip()
            preview = full_text[:3000] + "..." if len(full_text) > 3000 else full_text
            content_parts.append(preview)
        else:
            content_parts.append("[No text could be extracted]")

        content_parts.extend([
            "",
            "Analysis: PyPDF2 text extraction complete",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.error(f"PyPDF2 extraction failed for {pdf_uri}: {e}")
        return None

def extract_with_docai(pdf_uri: str) -> Optional[str]:
    """Extract text from PDF using Document AI."""

    try:
        # Download PDF
        bucket_name = pdf_uri.split('/')[2]
        blob_name = '/'.join(pdf_uri.split('/')[3:])

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        pdf_content = blob.download_as_bytes()

        # Create document
        document = documentai.RawDocument(
            content=pdf_content,
            mime_type="application/pdf"
        )

        # Process request
        request = documentai.ProcessRequest(
            name=PROCESSOR_NAME,
            raw_document=document
        )

        # Process document
        result = docai_client.process_document(request=request)
        document = result.document

        # Build content
        filename = pdf_uri.split('/')[-1]
        content_parts = [
            f"PDF File: {filename}",
            f"Location: {pdf_uri}",
            f"Pages: {len(document.pages)}",
            f"Extraction Method: Document AI (OCR)",
            "",
            "Content:",
        ]

        if document.text:
            text_preview = document.text[:3000].replace('\n\n\n', '\n\n').strip()
            content_parts.append(text_preview)

            if len(document.text) > 3000:
                content_parts.append(f"\n... [Document contains {len(document.text)} characters total]")
        else:
            content_parts.append("[No text extracted]")

        content_parts.extend([
            "",
            "Analysis: Document AI extraction complete",
            f"Indexed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        ])

        return '\n'.join(content_parts)

    except Exception as e:
        logger.debug(f"Document AI failed for {pdf_uri}: {e}")
        return None

def extract_pdf_hybrid(pdf_uri: str) -> Optional[str]:
    """Extract PDF using Document AI first, fallback to PyPDF2."""

    # Try Document AI first (better for scanned PDFs)
    content = extract_with_docai(pdf_uri)

    if content and "[No text extracted]" not in content:
        logger.info(f"✓ Extracted with Document AI: {pdf_uri.split('/')[-1]}")
        return content

    # Fallback to PyPDF2
    content = extract_with_pypdf2(pdf_uri)

    if content:
        logger.info(f"✓ Extracted with PyPDF2: {pdf_uri.split('/')[-1]}")
        return content

    logger.error(f"✗ Both methods failed: {pdf_uri.split('/')[-1]}")
    return None

def update_pdf_in_bigquery(uri: str, text_content: str) -> bool:
    """Update PDF in BigQuery."""

    query = """
    UPDATE `semgrep-472018.grepmm.search_corpus`
    SET text_content = @text_content,
        embedding = NULL  -- Clear embedding to force regeneration
    WHERE uri = @uri
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("uri", "STRING", uri),
            bigquery.ScalarQueryParameter("text_content", "STRING", text_content),
        ]
    )

    try:
        job = bq_client.query(query, job_config=job_config)
        job.result()
        return True
    except Exception as e:
        logger.error(f"Failed to update {uri}: {e}")
        return False

def main():
    """Process all PDFs with hybrid extraction."""

    logger.info("="*70)
    logger.info("Starting Hybrid PDF Extraction (Document AI + PyPDF2)")
    logger.info("="*70)

    # Get all PDF URIs
    query = """
    SELECT DISTINCT uri
    FROM `semgrep-472018.grepmm.search_corpus`
    WHERE modality = 'pdf'
    ORDER BY uri
    """

    results = bq_client.query(query).result()
    pdf_uris = [row.uri for row in results]

    logger.info(f"Found {len(pdf_uris)} PDFs to process")

    # Process all PDFs
    success_count = 0
    docai_count = 0
    pypdf_count = 0

    for i, uri in enumerate(pdf_uris, 1):
        logger.info(f"[{i}/{len(pdf_uris)}] Processing {uri.split('/')[-1]}...")

        content = extract_pdf_hybrid(uri)

        if content:
            if "Document AI" in content:
                docai_count += 1
            elif "PyPDF2" in content:
                pypdf_count += 1

            if update_pdf_in_bigquery(uri, content):
                success_count += 1
            else:
                logger.error(f"Failed to update BigQuery for {uri.split('/')[-1]}")
        else:
            logger.error(f"No content extracted from {uri.split('/')[-1]}")

        # Rate limiting
        if i < len(pdf_uris):
            time.sleep(0.5)

    # Summary
    logger.info("="*70)
    logger.info("Hybrid PDF Extraction Complete!")
    logger.info("="*70)
    logger.info(f"Total PDFs processed: {len(pdf_uris)}")
    logger.info(f"Successfully extracted: {success_count}")
    logger.info(f"  - Document AI: {docai_count}")
    logger.info(f"  - PyPDF2: {pypdf_count}")
    logger.info(f"  - Failed: {len(pdf_uris) - success_count}")

    if success_count > 0:
        logger.info("\nNext: Run 'uv run grepctl index --update' to regenerate embeddings")

if __name__ == "__main__":
    main()
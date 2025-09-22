"""
PDF processing and ingestion for semantic search using Document AI.
"""

import logging
from typing import Dict, List, Optional
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
from google.cloud import bigquery
from ..config import Config
from ..bigquery.connection import BigQueryClient

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDFs and ingest them for semantic search."""

    def __init__(self, client: BigQueryClient, config: Config):
        """Initialize PDF processor."""
        self.client = client
        self.config = config
        self.storage_client = storage.Client(project=config.project_id)
        self.docai_client = documentai.DocumentProcessorServiceClient()
        # Document AI processor ID (needs to be created in GCP Console)
        self.processor_name = "projects/936777684453/locations/us/processors/967b0c6daf70d715"

    def create_pdf_metadata_table(self) -> None:
        """Create a table to store PDF metadata and descriptions."""
        query = f"""
        CREATE TABLE IF NOT EXISTS `{self.config.project_id}.{self.config.dataset_name}.pdf_metadata` (
            pdf_id STRING,
            uri STRING,
            title STRING,
            description STRING,
            category STRING,
            tags ARRAY<STRING>,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        try:
            job = self.client.execute_query(query)
            job.result()
            logger.info("PDF metadata table created/verified")
        except Exception as e:
            logger.error(f"Failed to create PDF metadata table: {e}")

    def add_sample_pdf_metadata(self) -> None:
        """Add sample metadata for demo PDFs."""
        # Sample PDF descriptions based on common research papers and documents
        pdf_metadata = [
            ("semgrep-academic-whitepaper-draft-v4.pdf",
             "Semgrep Academic Whitepaper",
             "Academic whitepaper on semantic grep technology, discussing static analysis, pattern matching, and code security scanning techniques.",
             "research",
             ["semgrep", "static analysis", "security", "whitepaper", "academic"]),

            ("ml-papers/attention-is-all-you-need.pdf",
             "Attention Is All You Need",
             "Foundational paper introducing the Transformer architecture, self-attention mechanisms, and their applications in natural language processing.",
             "machine learning",
             ["transformer", "attention", "deep learning", "NLP", "neural networks"]),

            ("ml-papers/bert-paper.pdf",
             "BERT: Pre-training of Deep Bidirectional Transformers",
             "Paper introducing BERT (Bidirectional Encoder Representations from Transformers) for language understanding tasks.",
             "machine learning",
             ["BERT", "transformers", "NLP", "pre-training", "language models"]),

            ("security-reports/owasp-top-10-2021.pdf",
             "OWASP Top 10 Security Risks 2021",
             "Comprehensive guide to the top 10 web application security risks, including injection attacks, broken authentication, and security misconfigurations.",
             "security",
             ["OWASP", "security", "web security", "vulnerabilities", "best practices"]),

            ("documentation/bigquery-best-practices.pdf",
             "BigQuery Best Practices Guide",
             "Google Cloud BigQuery optimization guide covering query performance, cost optimization, and data modeling best practices.",
             "cloud computing",
             ["BigQuery", "Google Cloud", "SQL", "data warehouse", "optimization"]),

            ("research/vector-databases-survey.pdf",
             "Survey of Vector Database Systems",
             "Comprehensive survey of vector database systems, embedding techniques, and similarity search algorithms.",
             "database",
             ["vector database", "embeddings", "similarity search", "database systems"]),
        ]

        # Generate metadata for remaining PDFs
        for i in range(7, 32):  # We have 31 PDFs total
            category_rotation = ["research", "machine learning", "security", "cloud computing", "database"]
            category = category_rotation[i % len(category_rotation)]

            pdf_metadata.append(
                (f"document_{i:03d}.pdf",
                 f"Technical Document {i}",
                 f"Technical documentation covering various aspects of {category} systems, architectures, and best practices.",
                 category,
                 [category, "technical", "documentation", "guide"])
            )

        # Insert metadata into BigQuery
        self._insert_pdf_metadata(pdf_metadata)

    def _insert_pdf_metadata(self, metadata: List[tuple]) -> None:
        """Insert PDF metadata into BigQuery."""
        values = []

        # Get actual PDF URIs from obj_pdf table
        query = f"""
        SELECT uri, REGEXP_EXTRACT(uri, r'/([^/]+)$') as filename
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_pdf`
        """

        try:
            results = self.client.execute_query_and_wait(query)
            uri_map = {row['filename']: row['uri'] for row in results if row['filename']}

            for item in metadata[:31]:  # Limit to actual number of PDFs
                if len(item) == 5:
                    filename, title, desc, category, tags = item
                    # Try to match with actual URIs
                    actual_uri = None
                    for uri_filename, uri in uri_map.items():
                        if filename in uri_filename or uri_filename.endswith('.pdf'):
                            actual_uri = uri
                            uri_map.pop(uri_filename)  # Remove used URI
                            break

                    if actual_uri:
                        tags_str = "[" + ", ".join([f'"{tag}"' for tag in tags]) + "]"
                        # Escape single quotes in descriptions
                        desc_escaped = desc.replace("'", "''")
                        title_escaped = title.replace("'", "''")
                        values.append(f"('{filename}', '{actual_uri}', '{title_escaped}', '{desc_escaped}', '{category}', {tags_str})")

            if values:
                insert_query = f"""
                INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.pdf_metadata`
                (pdf_id, uri, title, description, category, tags)
                VALUES {', '.join(values)}
                """

                job = self.client.execute_query(insert_query)
                job.result()
                logger.info(f"Inserted {len(values)} PDF metadata records")
            else:
                logger.warning("No PDF metadata to insert")

        except Exception as e:
            logger.error(f"Failed to insert PDF metadata: {e}")

    def ingest_pdfs_with_metadata(self) -> int:
        """Ingest PDFs with their metadata into the documents table."""
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            COALESCE(m.uri, p.uri) AS uri,
            'pdf' AS modality,
            'pdf' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            COALESCE(
                CONCAT(
                    'PDF Document: ', COALESCE(m.title, REGEXP_EXTRACT(p.uri, r'/([^/]+)$')), '\\n\\n',
                    'Description: ', COALESCE(m.description, 'PDF document awaiting content extraction'), '\\n\\n',
                    'Category: ', COALESCE(m.category, 'general'), '\\n',
                    'Tags: ', COALESCE(ARRAY_TO_STRING(m.tags, ', '), 'pdf, document'), '\\n',
                    'Format: PDF\\n',
                    'Size: ', CAST(p.size AS STRING), ' bytes\\n',
                    'Note: Full text extraction requires Document AI or OCR processing'
                ),
                CONCAT(
                    'PDF File: ', REGEXP_EXTRACT(p.uri, r'/([^/]+)$'), '\\n',
                    'Format: PDF\\n',
                    'Size: ', CAST(p.size AS STRING), ' bytes\\n',
                    'Type: Portable Document Format\\n',
                    'Note: Awaiting content extraction'
                )
            ) AS text_content,
            p.content_type AS mime_type,
            TO_JSON(STRUCT(
                p.size,
                p.updated AS last_modified,
                p.generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.obj_pdf` p
        LEFT JOIN `{self.config.project_id}.{self.config.dataset_name}.pdf_metadata` m
        ON p.uri = m.uri
        WHERE p.uri NOT IN (
            SELECT DISTINCT uri FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
            WHERE modality = 'pdf'
        )
        """

        try:
            job = self.client.execute_query(query)
            job.result(timeout=300)
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Ingested {num_rows} PDFs with metadata")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to ingest PDFs: {e}")
            return 0

    def extract_pdf_with_document_ai(self, pdf_uri: str) -> Optional[str]:
        """Extract text from a PDF using Document AI."""
        try:
            # Parse GCS URI
            bucket_name = pdf_uri.split('/')[2]
            blob_name = '/'.join(pdf_uri.split('/')[3:])

            # Download PDF from GCS
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            pdf_content = blob.download_as_bytes()

            # Create Document AI request
            document = documentai.Document(
                content=pdf_content,
                mime_type="application/pdf",
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=documentai.RawDocument(
                    content=pdf_content,
                    mime_type="application/pdf",
                ),
            )

            # Process the document
            result = self.docai_client.process_document(request=request)
            document = result.document

            # Extract text
            text = document.text
            logger.info(f"Extracted {len(text)} characters from {blob_name}")
            return text

        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_uri}: {e}")
            return None

    def process_pdfs_with_document_ai(self) -> int:
        """Process all PDFs with Document AI and update their content."""
        # Get all PDFs that need processing
        query = f"""
        SELECT uri, doc_id
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        WHERE modality = 'pdf'
        AND NOT CONTAINS_SUBSTR(text_content, 'Extracted Text:')
        LIMIT 5
        """

        try:
            results = self.client.execute_query_and_wait(query)
            processed_count = 0

            for row in results:
                pdf_uri = row['uri']
                doc_id = row['doc_id']
                logger.info(f"Processing {pdf_uri} with Document AI...")

                # Extract text using Document AI
                extracted_text = self.extract_pdf_with_document_ai(pdf_uri)

                if extracted_text:
                    # Update the document with extracted text
                    # Truncate if too long (BigQuery string limit)
                    if len(extracted_text) > 50000:
                        extracted_text = extracted_text[:50000] + "...[truncated]"

                    # Use parameterized query to avoid SQL injection and escaping issues
                    update_query = """
                    UPDATE `{}.{}.documents`
                    SET text_content = CONCAT(
                        REGEXP_REPLACE(text_content, r'Note: Full text extraction.*$', ''),
                        '\\n\\nExtracted Text:\\n',
                        @extracted_text
                    )
                    WHERE doc_id = @doc_id
                    """.format(self.config.project_id, self.config.dataset_name)

                    job_config = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("doc_id", "STRING", doc_id),
                            bigquery.ScalarQueryParameter("extracted_text", "STRING", extracted_text),
                        ]
                    )

                    self.client.execute_query(update_query, job_config).result()
                    processed_count += 1
                    logger.info(f"Updated document {doc_id} with extracted text")

            # Also update in search_corpus
            if processed_count > 0:
                sync_query = f"""
                UPDATE `{self.config.project_id}.{self.config.dataset_name}.search_corpus` sc
                SET sc.text_content = d.text_content
                FROM `{self.config.project_id}.{self.config.dataset_name}.documents` d
                WHERE sc.doc_id = d.doc_id
                AND d.modality = 'pdf'
                AND d.text_content LIKE '%Extracted Text:%'
                """
                self.client.execute_query(sync_query).result()

            logger.info(f"Processed {processed_count} PDFs with Document AI")
            return processed_count

        except Exception as e:
            logger.error(f"Failed to process PDFs with Document AI: {e}")
            return 0

    def update_search_corpus(self) -> int:
        """Update search corpus with PDF documents."""
        query = f"""
        INSERT INTO `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
        SELECT
            doc_id,
            uri,
            modality,
            source,
            created_at,
            author,
            channel,
            text_content,
            mime_type,
            meta,
            chunk_index,
            chunk_start,
            chunk_end,
            embedding
        FROM `{self.config.project_id}.{self.config.dataset_name}.documents`
        WHERE modality = 'pdf'
        AND doc_id NOT IN (
            SELECT doc_id FROM `{self.config.project_id}.{self.config.dataset_name}.search_corpus`
            WHERE modality = 'pdf'
        )
        """

        try:
            job = self.client.execute_query(query)
            job.result(timeout=300)
            num_rows = job.num_dml_affected_rows or 0
            logger.info(f"Added {num_rows} PDFs to search corpus")
            return num_rows
        except Exception as e:
            logger.error(f"Failed to update search corpus: {e}")
            return 0
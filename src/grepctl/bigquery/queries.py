"""
SQL query templates for BigQuery operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryTemplates:
    """SQL query templates for BigQuery operations."""

    @staticmethod
    def insert_document(project_id: str, dataset: str) -> str:
        """Template for inserting a document."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        (doc_id, uri, modality, source, created_at, author, channel,
         text_content, mime_type, meta, chunk_index, chunk_start, chunk_end, embedding)
        VALUES
        (@doc_id, @uri, @modality, @source, @created_at, @author, @channel,
         @text_content, @mime_type, @meta, @chunk_index, @chunk_start, @chunk_end, @embedding)
        """

    @staticmethod
    def extract_text_from_pdf(project_id: str, dataset: str, text_model: str) -> str:
        """Query to extract text from PDF files."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'pdf' AS modality,
            'pdf' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            SAFE_CONVERT_BYTES_TO_STRING(data) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_pdf`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE modality = 'pdf'
        )
        """

    @staticmethod
    def extract_text_from_images(project_id: str, dataset: str, text_model: str) -> str:
        """Query to perform OCR on images."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'image' AS modality,
            'screenshot' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            CONCAT(
                'Image file: ', SPLIT(uri, '/')[ARRAY_LENGTH(SPLIT(uri, '/')) - 1], '\\n',
                'Type: ', content_type, '\\n',
                'Size: ', CAST(size AS STRING), ' bytes\\n',
                'Note: OCR text extraction requires ML model configuration'
            ) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_images`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE modality = 'image'
        )
        """

    @staticmethod
    def extract_text_from_audio(project_id: str, dataset: str, text_model: str) -> str:
        """Query to transcribe audio files."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'audio' AS modality,
            'recording' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            CONCAT(
                'Audio file: ', SPLIT(uri, '/')[ARRAY_LENGTH(SPLIT(uri, '/')) - 1], '\\n',
                'Type: ', content_type, '\\n',
                'Size: ', CAST(size AS STRING), ' bytes\\n',
                'Note: Audio transcription requires ML model configuration'
            ) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_audio`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE modality = 'audio'
        )
        """

    @staticmethod
    def extract_text_from_video(project_id: str, dataset: str, text_model: str) -> str:
        """Query to transcribe video files."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'video' AS modality,
            'video' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            CONCAT(
                'Video file: ', SPLIT(uri, '/')[ARRAY_LENGTH(SPLIT(uri, '/')) - 1], '\\n',
                'Type: ', content_type, '\\n',
                'Size: ', CAST(size AS STRING), ' bytes\\n',
                'Note: Video transcription requires ML model configuration'
            ) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_video`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE modality = 'video'
        )
        """

    @staticmethod
    def ingest_text_files(project_id: str, dataset: str) -> str:
        """Query to ingest plain text files."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'file' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_text`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE modality = 'text'
        )
        """

    @staticmethod
    def ingest_markdown_files(project_id: str, dataset: str) -> str:
        """Query to ingest markdown files."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'markdown' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_markdown`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE source = 'markdown'
        )
        """

    @staticmethod
    def summarize_json_files(project_id: str, dataset: str, text_model: str) -> str:
        """Query to summarize JSON files for search."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'json' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_json`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE source = 'json'
        )
        """

    @staticmethod
    def summarize_csv_files(project_id: str, dataset: str, text_model: str) -> str:
        """Query to summarize CSV files for search."""
        return f"""
        INSERT INTO `{project_id}.{dataset}.documents`
        SELECT
            GENERATE_UUID() AS doc_id,
            uri AS uri,
            'text' AS modality,
            'csv' AS source,
            CURRENT_TIMESTAMP() AS created_at,
            CAST(NULL AS STRING) AS author,
            CAST(NULL AS STRING) AS channel,
            SAFE_CAST(data AS STRING) AS text_content,
            content_type AS mime_type,
            TO_JSON(STRUCT(
                size,
                updated AS last_modified,
                generation
            )) AS meta,
            CAST(NULL AS INT64) AS chunk_index,
            CAST(NULL AS INT64) AS chunk_start,
            CAST(NULL AS INT64) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM `{project_id}.{dataset}.obj_csv`
        WHERE uri NOT IN (
            SELECT DISTINCT uri FROM `{project_id}.{dataset}.documents`
            WHERE source = 'csv'
        )
        """

    @staticmethod
    def chunk_documents(project_id: str, dataset: str, chunk_size: int, chunk_overlap: int) -> str:
        """Query to chunk long documents."""
        max_chunk_size = chunk_size + chunk_overlap

        return f"""
        CREATE OR REPLACE TABLE `{project_id}.{dataset}.document_chunks`
        PARTITION BY DATE(created_at)
        CLUSTER BY modality, source AS
        WITH base AS (
            SELECT * FROM `{project_id}.{dataset}.documents`
            WHERE text_content IS NOT NULL
            AND LENGTH(text_content) > {chunk_size * 2}
        ),
        chunk_positions AS (
            SELECT
                doc_id,
                uri,
                modality,
                source,
                created_at,
                author,
                channel,
                mime_type,
                meta,
                text_content,
                chunk_num,
                chunk_num * {chunk_size - chunk_overlap} AS chunk_start
            FROM base,
            UNNEST(GENERATE_ARRAY(
                0,
                CAST(CEIL(LENGTH(text_content) / {chunk_size - chunk_overlap}) AS INT64) - 1
            )) AS chunk_num
        )
        SELECT
            CONCAT(doc_id, ':', CAST(chunk_num AS STRING)) AS doc_id,
            uri,
            modality,
            source,
            created_at,
            author,
            channel,
            SUBSTR(text_content, chunk_start + 1, {max_chunk_size}) AS text_content,
            mime_type,
            meta,
            chunk_num AS chunk_index,
            chunk_start,
            LEAST(chunk_start + {max_chunk_size}, LENGTH(text_content)) AS chunk_end,
            CAST(NULL AS ARRAY<FLOAT64>) AS embedding
        FROM chunk_positions
        """

    @staticmethod
    def create_search_corpus(project_id: str, dataset: str, chunk_size: int) -> str:
        """Query to create unified search corpus."""
        return f"""
        CREATE OR REPLACE TABLE `{project_id}.{dataset}.search_corpus`
        PARTITION BY DATE(created_at)
        CLUSTER BY modality, source AS
        -- Include all chunks
        SELECT * FROM `{project_id}.{dataset}.document_chunks`
        UNION ALL
        -- Include short documents that don't need chunking
        SELECT * FROM `{project_id}.{dataset}.documents`
        WHERE text_content IS NOT NULL
        AND LENGTH(text_content) <= {chunk_size * 2}
        AND doc_id NOT IN (
            SELECT DISTINCT SPLIT(doc_id, ':')[OFFSET(0)]
            FROM `{project_id}.{dataset}.document_chunks`
        )
        """

    @staticmethod
    def generate_embeddings(project_id: str, dataset: str, embedding_model: str, batch_size: int = 100) -> str:
        """Query to generate embeddings for documents."""
        return f"""
        UPDATE `{project_id}.{dataset}.search_corpus` AS sc
        SET embedding = emb.ml_generate_embedding_result
        FROM (
            SELECT
                doc_id,
                ml_generate_embedding_result
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{embedding_model}`,
                (
                    SELECT
                        doc_id,
                        text_content AS content
                    FROM `{project_id}.{dataset}.search_corpus`
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

    @staticmethod
    def get_documents_needing_embeddings(project_id: str, dataset: str, limit: int = 1000) -> str:
        """Query to find documents without embeddings."""
        return f"""
        SELECT
            doc_id,
            text_content,
            LENGTH(text_content) AS text_length
        FROM `{project_id}.{dataset}.search_corpus`
        WHERE (embedding IS NULL OR ARRAY_LENGTH(embedding) = 0)
        AND text_content IS NOT NULL
        AND LENGTH(text_content) > 0
        ORDER BY created_at DESC
        LIMIT {limit}
        """

    @staticmethod
    def update_document_embedding(project_id: str, dataset: str) -> str:
        """Query to update a single document's embedding."""
        return f"""
        UPDATE `{project_id}.{dataset}.search_corpus`
        SET embedding = @embedding
        WHERE doc_id = @doc_id
        """

    @staticmethod
    def semantic_search(project_id: str, dataset: str, embedding_model: str,
                        top_k: int, use_rerank: bool = False) -> str:
        """Query template for semantic search."""
        return f"""
        WITH query_embedding AS (
            SELECT ml_generate_embedding_result AS embedding
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{embedding_model}`,
                (SELECT @query AS content)
            )
        ),
        search_results AS (
            SELECT
                doc_id,
                uri,
                modality,
                source,
                created_at,
                author,
                channel,
                text_content,
                distance
            FROM query_embedding,
            VECTOR_SEARCH(
                TABLE `{project_id}.{dataset}.search_corpus`,
                'embedding',
                (SELECT embedding FROM query_embedding),
                top_k => {top_k}
            )
        )
        SELECT * FROM search_results
        ORDER BY distance ASC
        """

    @staticmethod
    def get_modality_stats(project_id: str, dataset: str) -> str:
        """Query to get statistics by modality."""
        return f"""
        SELECT
            modality,
            source,
            COUNT(*) AS document_count,
            COUNT(DISTINCT uri) AS unique_files,
            AVG(LENGTH(text_content)) AS avg_text_length,
            MAX(created_at) AS latest_update
        FROM `{project_id}.{dataset}.documents`
        GROUP BY modality, source
        ORDER BY document_count DESC
        """
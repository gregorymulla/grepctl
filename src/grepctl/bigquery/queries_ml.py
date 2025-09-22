"""
SQL query templates for BigQuery operations using ML.GENERATE_TEXT.
These queries require proper Vertex AI model setup.
"""

from typing import Optional, List, Dict, Any


class MLQueryTemplates:
    """SQL query templates for BigQuery ML operations."""

    @staticmethod
    def extract_text_from_pdf_ml(project_id: str, dataset: str, text_model: str) -> str:
        """Extract text from PDF files using ML.GENERATE_TEXT."""
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
            ML.GENERATE_TEXT(
                MODEL `{text_model}`,
                CONCAT(
                    'Extract all text content from this PDF. ',
                    'Preserve structure, headings, and important information. ',
                    'Output clean, readable text only.'
                ),
                data
            ).ml_generate_text_result AS text_content,
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
    def extract_text_from_images_ml(project_id: str, dataset: str, text_model: str) -> str:
        """Perform OCR on images using ML.GENERATE_TEXT."""
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
            ML.GENERATE_TEXT(
                MODEL `{text_model}`,
                CONCAT(
                    'Perform OCR on this image. ',
                    'Extract all visible text. ',
                    'If text is sparse, describe the visual content briefly.'
                ),
                data
            ).ml_generate_text_result AS text_content,
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
    def extract_text_from_audio_ml(project_id: str, dataset: str, text_model: str) -> str:
        """Transcribe audio files using ML.GENERATE_TEXT."""
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
            ML.GENERATE_TEXT(
                MODEL `{text_model}`,
                'Transcribe this audio file. Include speaker turns if identifiable.',
                data
            ).ml_generate_text_result AS text_content,
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
    def extract_text_from_video_ml(project_id: str, dataset: str, text_model: str) -> str:
        """Transcribe video files using ML.GENERATE_TEXT."""
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
            ML.GENERATE_TEXT(
                MODEL `{text_model}`,
                CONCAT(
                    'Transcribe all spoken content in this video. ',
                    'Include rough timestamps if possible. ',
                    'Note any important visual elements that provide context.'
                ),
                data
            ).ml_generate_text_result AS text_content,
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
    def rerank_with_llm(project_id: str, dataset: str, text_model: str,
                        query: str, top_k: int = 10) -> str:
        """Rerank search results using LLM for better precision."""
        return f"""
        WITH candidates AS (
            -- First get vector search results
            SELECT
                doc_id,
                uri,
                modality,
                source,
                text_content,
                distance
            FROM query_embedding,
            VECTOR_SEARCH(
                TABLE `{project_id}.{dataset}.search_corpus`,
                'embedding',
                (SELECT embedding FROM query_embedding),
                top_k => {top_k * 3}  -- Get more candidates for reranking
            )
        ),
        reranked AS (
            SELECT
                doc_id,
                uri,
                modality,
                source,
                text_content,
                distance,
                ML.GENERATE_TEXT(
                    MODEL `{text_model}`,
                    CONCAT(
                        'Rate the relevance of this document to the query on a scale of 0-10.',
                        '\\nQuery: ', @query,
                        '\\nDocument: ', SUBSTR(text_content, 0, 1000),
                        '\\nReturn only a number between 0-10.'
                    )
                ).ml_generate_text_result AS relevance_score
            FROM candidates
        )
        SELECT
            doc_id,
            uri,
            modality,
            source,
            text_content,
            distance,
            CAST(relevance_score AS FLOAT64) AS relevance_score
        FROM reranked
        ORDER BY relevance_score DESC
        LIMIT {top_k}
        """
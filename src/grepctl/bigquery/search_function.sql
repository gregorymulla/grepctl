-- BigQuery Search Function for Grepctl
-- This function simplifies semantic search by wrapping the VECTOR_SEARCH complexity

CREATE OR REPLACE FUNCTION `{project_id}.{dataset_name}.semantic_search`(
    query_text STRING,
    top_k INT64,
    min_relevance FLOAT64
)
AS (
    (
        SELECT
            doc.doc_id,
            doc.uri,
            doc.source,
            doc.modality,
            doc.text_content,
            ROUND((1.0 - distance), 3) AS relevance_score,
            doc.created_at,
            doc.metadata
        FROM VECTOR_SEARCH(
            TABLE `{project_id}.{dataset_name}.search_corpus`,
            'embedding',
            (
                SELECT ml_generate_embedding_result
                FROM ML.GENERATE_EMBEDDING(
                    MODEL `{project_id}.{dataset_name}.text_embedding_model`,
                    (SELECT query_text AS content),
                    STRUCT(TRUE AS flatten_json_output)
                )
            ),
            top_k => IFNULL(top_k, 10),
            distance_type => 'COSINE'
        ) AS doc
        WHERE (1.0 - distance) >= IFNULL(min_relevance, 0.0)
        ORDER BY distance ASC
    )
);

-- Simplified search with just query text (uses defaults)
CREATE OR REPLACE FUNCTION `{project_id}.{dataset_name}.search`(
    query_text STRING
)
AS (
    `{project_id}.{dataset_name}.semantic_search`(query_text, 10, 0.0)
);

-- Search with source filtering
CREATE OR REPLACE FUNCTION `{project_id}.{dataset_name}.search_by_source`(
    query_text STRING,
    sources ARRAY<STRING>,
    top_k INT64
)
AS (
    (
        SELECT *
        FROM `{project_id}.{dataset_name}.semantic_search`(query_text, IFNULL(top_k, 10), 0.0)
        WHERE source IN UNNEST(sources)
    )
);

-- Search with date range filtering
CREATE OR REPLACE FUNCTION `{project_id}.{dataset_name}.search_by_date`(
    query_text STRING,
    start_date DATE,
    end_date DATE,
    top_k INT64
)
AS (
    (
        SELECT *
        FROM `{project_id}.{dataset_name}.semantic_search`(query_text, IFNULL(top_k, 10), 0.0)
        WHERE DATE(created_at) BETWEEN start_date AND end_date
    )
);

-- Get just content strings (similar to search_simple in Python)
CREATE OR REPLACE FUNCTION `{project_id}.{dataset_name}.search_content`(
    query_text STRING,
    limit_count INT64
)
AS (
    (
        SELECT text_content
        FROM `{project_id}.{dataset_name}.semantic_search`(query_text, IFNULL(limit_count, 5), 0.0)
    )
);
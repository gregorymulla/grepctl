Purpose: Enable SQL-native “semantic grep” across heterogeneous data in gs://gcm-data-lake/multimodal-dataset/ (text, PDF, images, audio, video, CSV/JSON/MD).

1) Overview

Semantic Grep provides:

Unified ingestion from GCS object folders into a canonical table.

Text extraction (OCR/transcription) for non-text media.

Embeddings + vector index for semantic KNN search.

Hybrid filters (regex, time, source).

LLM rerank (optional) for precision@K.

SQL-native invocation via a Table Function and Stored Procedure.

2) Goals & Non-Goals

Goals

One SQL endpoint to search across all modalities.

Minimal friction to add new modalities/sources.

Reasonable latency at millions of rows with IVF vector index.

Non-Goals

Full MAM (media asset management).

Frame extraction/keyframe indexing (can be added later).

Live streaming ingestion (batch assumed).

3) Data Layout (GCS)
gs://gcm-data-lake/multimodal-dataset/
  audio/
  csv/
  documents/
  images/
  json/
  markdown/
  pdf/
  text/
  video/


Each leaf holds files (any folder depth). We expose these via BigQuery Object Tables.

4) Dataset & Models

BigQuery Dataset: mmgrep

Models (configure once):

text_model – LLM for OCR/transcription/summarization (e.g., Gemini).

embedding_model – text embedding (e.g., text-embedding-004).

DECLARE text_model STRING DEFAULT
  'projects/your-project/locations/your-region/publishers/google/models/gemini-1.5-pro';
DECLARE embedding_model STRING DEFAULT
  'projects/your-project/locations/your-region/publishers/google/models/text-embedding-004';

5) Canonical Schema
CREATE SCHEMA IF NOT EXISTS `mmgrep`;

CREATE OR REPLACE TABLE `mmgrep.documents` (
  doc_id STRING,
  uri STRING,                  -- gs://... (or synthetic for chunks)
  modality STRING,             -- 'text'|'pdf'|'image'|'audio'|'video'|'json'|'csv'|'md'
  source STRING,               -- 'file'|'pdf'|'screenshot'|'recording'|'video'|...
  created_at TIMESTAMP,
  author STRING,
  channel STRING,
  text_content STRING,         -- OCR/transcript/normalized text
  mime_type STRING,
  meta JSON,                   -- arbitrary metadata (object headers etc.)
  chunk_index INT64,           -- 0-based if chunked; NULL otherwise
  chunk_start INT64,           -- char offset
  chunk_end INT64,             -- char offset
  embedding ARRAY<FLOAT64>     -- vector for semantic search
)
PARTITION BY DATE(created_at)
CLUSTER BY modality, source;


Optional: keep a separate assets table for raw objects; not required for search.

6) Object Tables (GCS Connection)

Replace <<<CONNECTION_NAME>>> with your BigQuery GCS connection.

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_pdf`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/pdf/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_images`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/images/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_audio`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/audio/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_video`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/video/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_text`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/text/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_markdown`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/markdown/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_json`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/json/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_csv`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/csv/**']);

CREATE OR REPLACE EXTERNAL TABLE `mmgrep.obj_documents`
WITH CONNECTION `<<<CONNECTION_NAME>>>`
OPTIONS (object_metadata='SIMPLE', uris=['gs://gcm-data-lake/multimodal-dataset/documents/**']);

7) Text Extraction (OCR / Transcription / Normalization)

PDF → text

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'pdf', 'pdf', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Extract clean, readable text from this PDF. Preserve headings.' AS prompt,
    obj AS content, text_model AS model
  )) AS text_content,
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_pdf`;


Images → OCR

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'image', 'screenshot', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Perform OCR; if sparse, summarize visible UI text.' AS prompt,
    obj AS content, text_model AS model
  )),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_images`;


Audio → transcript

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'audio', 'recording', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Transcribe the audio; include speaker turns if possible.' AS prompt,
    obj AS content, text_model AS model
  )),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_audio`;


Video → transcript (direct if supported; else pre-extract audio)

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'video', 'video', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Transcribe spoken content in the video; include rough timestamps.' AS prompt,
    obj AS content, text_model AS model
  )),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_video`;


Text / MD (direct)

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'text', 'file', CURRENT_TIMESTAMP(),
  NULL, NULL, SAFE_CAST(obj AS STRING),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_text`;

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'text', 'markdown', CURRENT_TIMESTAMP(),
  NULL, NULL, SAFE_CAST(obj AS STRING),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_markdown`;


JSON / CSV → natural language summary (searchable)

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'text', 'json', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Summarize key fields/records in natural language for search. Keep entities and numbers.' AS prompt,
    obj AS content, text_model AS model
  )),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_json`;

INSERT INTO `mmgrep.documents`
SELECT
  GENERATE_UUID(), _FILE_NAME, 'text', 'csv', CURRENT_TIMESTAMP(),
  NULL, NULL,
  AI.GENERATE(STRUCT(
    'Summarize table columns and notable rows in natural language for search.' AS prompt,
    obj AS content, text_model AS model
  )),
  metadata.content_type, TO_JSON(STRUCT(metadata)),
  NULL, NULL, NULL, NULL
FROM `mmgrep.obj_csv`;

8) Chunking (recommended for long docs)
CREATE OR REPLACE TABLE `mmgrep.document_chunks` AS
WITH base AS (
  SELECT * FROM `mmgrep.documents`
  WHERE text_content IS NOT NULL AND LENGTH(text_content) > 2000
),
exploded AS (
  SELECT
    doc_id, uri, modality, source, created_at, author, channel, mime_type, meta,
    GENERATE_ARRAY(0, LENGTH(text_content), 1000) AS starts,
    text_content
  FROM base
),
chunks AS (
  SELECT
    CONCAT(doc_id, ':', CAST(OFFSET AS STRING)) AS doc_id,
    uri, modality, source, created_at, author, channel,
    SUBSTR(text_content, starts[OFFSET] + 1, 1200) AS text_content,
    mime_type, meta,
    OFFSET AS chunk_index,
    starts[OFFSET] AS chunk_start,
    starts[OFFSET] + 1200 AS chunk_end,
    NULL AS embedding
  FROM exploded, UNNEST(starts) WITH OFFSET
)
SELECT * FROM chunks;

CREATE OR REPLACE TABLE `mmgrep.search_corpus` AS
SELECT doc_id, uri, modality, source, created_at, author, channel, text_content,
       mime_type, meta, chunk_index, chunk_start, chunk_end, embedding
FROM `mmgrep.document_chunks`
UNION ALL
SELECT doc_id, uri, modality, source, created_at, author, channel, text_content,
       mime_type, meta, NULL, NULL, NULL, embedding
FROM `mmgrep.documents`
WHERE text_content IS NOT NULL AND LENGTH(text_content) <= 2000;

9) Embeddings & Vector Index
UPDATE `mmgrep.search_corpus`
SET embedding = ML.GENERATE_EMBEDDING(MODEL embedding_model, text_content)
WHERE embedding IS NULL AND text_content IS NOT NULL;

CREATE OR REPLACE VECTOR INDEX `mmgrep.search_corpus_idx`
ON `mmgrep.search_corpus` (embedding)
OPTIONS (distance_type='COSINE', index_type='IVF', ivf_min_train_size=10000);

10) Invocation Surfaces
10.1 Table Function (preferred — composable in SQL)
CREATE OR REPLACE TABLE FUNCTION `mmgrep.semantic_grep_tf`(
  q STRING,
  top_k INT64,
  source_filter ARRAY<STRING>,      -- e.g. ['pdf','screenshot','recording','video','file','json','csv']
  start_ts TIMESTAMP,
  end_ts TIMESTAMP,
  regex STRING,                     -- e.g. r'(?i)invoice|churn|blackout'
  use_rerank BOOL                   -- LLM re-score 0..1
)
RETURNS TABLE<
  doc_id STRING, uri STRING, modality STRING, source STRING,
  created_at TIMESTAMP, author STRING, channel STRING,
  distance FLOAT64, rel_score FLOAT64, text_content STRING
>
AS (
  WITH qv AS (
    SELECT ML.GENERATE_EMBEDDING(MODEL embedding_model, q) AS v
  ),
  knn AS (
    SELECT
      s.doc_id, s.uri, s.modality, s.source, s.created_at, s.author, s.channel,
      s.distance, s.text_content
    FROM qv,
    VECTOR_SEARCH(TABLE `mmgrep.search_corpus`, 'embedding', qv.v,
      STRUCT(GREATEST(top_k*5, 50) AS top_k, 200 AS options_search_count)) s
    WHERE (ARRAY_LENGTH(source_filter)=0 OR s.source IN UNNEST(source_filter))
      AND s.created_at BETWEEN start_ts AND end_ts
      AND (regex IS NULL OR regex='' OR REGEXP_CONTAINS(s.text_content, regex))
  ),
  scored AS (
    SELECT k.*,
      CASE WHEN use_rerank THEN
        AI.GENERATE_DOUBLE(STRUCT(
          CONCAT('Query: ', q, '\nSnippet: ', SUBSTR(k.text_content,1,1500),
                 '\nReturn a single relevance score between 0 and 1.') AS prompt,
          text_model AS model
        ))
      ELSE NULL END AS rel_score
    FROM knn k
  )
  SELECT * FROM scored
  ORDER BY COALESCE(rel_score, 0) DESC, distance ASC
  LIMIT top_k
);


Examples

-- Cross-modal search, last year, finance language gate, with rerank
SELECT * FROM `mmgrep.semantic_grep_tf`(
  'onboarding invoices causing churn',
  20,
  ['pdf','screenshot','recording','video','file'],
  TIMESTAMP('2024-01-01'), TIMESTAMP('2024-12-31'),
  r'(?i)invoice|onboard|churn',
  TRUE
);

-- PDFs + screenshots only, no rerank
SELECT * FROM `mmgrep.semantic_grep_tf`(
  'energy crisis load shedding',
  15,
  ['pdf','screenshot'],
  TIMESTAMP('2023-01-01'), CURRENT_TIMESTAMP(),
  r'(?i)energy|blackout|load',
  FALSE
);

10.2 Stored Procedure (quick CALL)
CREATE OR REPLACE PROCEDURE `mmgrep.semantic_grep`(q STRING, k INT64)
BEGIN
  DECLARE v ARRAY<FLOAT64> DEFAULT ML.GENERATE_EMBEDDING(MODEL embedding_model, q);

  CREATE TEMP TABLE candidates AS
  SELECT sc.*, distance
  FROM VECTOR_SEARCH(TABLE `mmgrep.search_corpus`, 'embedding', v,
         STRUCT(GREATEST(k*5, 50) AS top_k, 200 AS options_search_count)) s
  JOIN `mmgrep.search_corpus` sc USING (doc_id);

  CREATE TEMP TABLE scored AS
  SELECT c.*,
    AI.GENERATE_DOUBLE(STRUCT(
      CONCAT('Query: ', q, '\nSnippet: ', SUBSTR(c.text_content,1,1500),
             '\nReturn a relevance score 0..1 only.') AS prompt,
      text_model AS model
    )) AS rel_score
  FROM candidates c;

  SELECT doc_id, uri, modality, source, created_at, author, channel,
         rel_score, distance, text_content
  FROM scored
  ORDER BY rel_score DESC, distance ASC
  LIMIT k;
END;


Example

CALL `mmgrep.semantic_grep`('first signs of invoice confusion after onboarding', 25);

11) “What are we grepping?” – Query Scenarios

Corporate memory: earliest mentions of shadow accounting across PDFs, screenshots, and recordings.

Media/support: all references to onboarding errors in screenshots, CSV/JSON summaries, and call transcripts.

Incident forensics: clips mentioning blackouts / load shedding plus related PDF reports.

12) Quality, Performance, Cost

Chunking: improves recall for long docs (1.2k chars, 200 overlap suggested).

Dedup: hash raw bytes or normalized text_content to skip re-embedding unchanged assets.

Partitions: ensure accurate created_at; prefer object mtime when available.

Index: rebuild after large batches; incremental updates otherwise.

Latency: retrieve top_k*5, rerank ≤200 candidates.

Guardrails: use AI.GENERATE_BOOL for PII/info policy checks before UI display.

Observability: log query/result pairs to evaluate recall@20, MRR.

Drill-down: keep uri so UI can deep-link to GCS; store timecodes in meta for A/V later.

13) Operations

Refresh cadence:

Ingestion (OCR/transcribe/summarize): daily.

Embeddings: upsert on new/changed rows.

Vector index: weekly rebuild or on threshold.

Access control:

Dataset-level IAM; restrict AI.GENERATE* usage if needed.

PII scanning for certain sources.

Disaster recovery:

GCS as source of truth; BQ tables re-creatable from object tables + extraction jobs.



14) Quick Start (Minimal Run Order)

Create dataset + declare text_model & embedding_model.

Create Object Tables (Section 6).

Run extraction inserts (Section 7).

(Optional) Run chunking (Section 8).

Generate embeddings & vector index (Section 9).

Create table function and procedure (Section 10).

Issue example queries (Section 10).